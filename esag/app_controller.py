"""E-SAG Application Controller. Wires all modules via Event Bus."""
import sys
import threading
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .events import bus
from .config import load_config, save_config
from .types import (
    AppConfig,
    EventType,
    FileCreatedEvent,
    FileModifiedEvent,
    FileDeletedEvent,
    FileMovedEvent,
    AlertEvent,
    AlertSeverity,
)

# Import existing modules (adapted to emit events)
from monitoring.file_monitor import start_all_folders, stop_all_folders, ACTIVE_OBSERVERS
from monitoring.folder_manager import get_monitored_folders
from database.database import create_database
from esag.ml.train_eval import run_experiment


class AppController:
    def __init__(self):
        self.config: AppConfig = load_config()
        self.running = False
        self.gui = None
        self._monitor_thread: threading.Thread | None = None

    def start(self) -> None:
        """Initialize database, start monitors, launch GUI."""
        print("[E-SAG] Starting...")

        # Ensure DB exists
        create_database()

        # Sync config folders to folder_manager DB
        self._sync_watched_folders()

        # Start file monitoring in background thread
        self._start_file_monitor()

        # Subscribe to events for rule engine / GUI
        self._setup_subscriptions()

        # Launch GUI (blocks until window closes)
        self._launch_gui()

        # Cleanup
        self.stop()

    def _sync_watched_folders(self) -> None:
        """Ensure folder_manager DB matches config."""
        from monitoring.folder_manager import add_folder, remove_folder
        from database.database import load_monitored_folders

        saved = set(load_monitored_folders())
        desired = set(self.config.watched_folders)

        for folder in desired - saved:
            add_folder(folder)
        for folder in saved - desired:
            remove_folder(folder)

    def _start_file_monitor(self) -> None:
        """Start watchdog observers in background thread."""
        self.running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _monitor_loop(self) -> None:
        """Background loop: start_all_folders, keep alive."""
        start_all_folders()
        while self.running:
            time.sleep(self.config.refresh_interval_sec)

    def _setup_subscriptions(self) -> None:
        """Wire event handlers: rule engine, DB persistence, GUI updates."""
        # File events -> DB (replaces direct DB calls in file_monitor.py)
        bus.subscribe(FileCreatedEvent, self._on_file_event)
        bus.subscribe(FileModifiedEvent, self._on_file_event)
        bus.subscribe(FileDeletedEvent, self._on_file_event)
        bus.subscribe(FileMovedEvent, self._on_file_event)

        # Alerts -> GUI (will be connected when GUI loads)
        bus.subscribe(AlertEvent, self._on_alert)

    def _on_file_event(self, event) -> None:
        """Persist file event to SQLite."""
        from database.database import insert_event
        try:
            insert_event(
                event.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                event.event_type.value,
                str(event.path),
                str(event.dest_path) if event.dest_path else None,
                event.is_directory,
            )
        except Exception as e:
            print(f"DB insert error: {e}")

    def _on_alert(self, event: AlertEvent) -> None:
        """Forward alert to GUI if loaded."""
        if self.gui and hasattr(self.gui, "add_alert"):
            self.gui.add_alert(event)

    def stop(self) -> None:
        """Stop monitors, save config."""
        print("[E-SAG] Stopping...")
        self.running = False
        stop_all_folders()
        save_config(self.config)
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)

    def _launch_gui(self) -> None:
        """Create and run PySide6 application."""
        app = QApplication.instance() or QApplication(sys.argv)
        from .gui.main_window import MainWindow
        self.gui = MainWindow(self.config, bus)
        self.gui.show()
        app.exec()


def main() -> None:
    controller = AppController()
    controller.start()


if __name__ == "__main__":
    main()