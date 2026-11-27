"""E-SAG Main Window. PySide6 dashboard skeleton."""
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QFileDialog, QMessageBox, QHeaderView, QSplitter
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QAction

from ..events import bus
from ..config import add_watched_folder, remove_watched_folder
from ..types import AppConfig, AlertEvent, AlertSeverity, FileCreatedEvent


class AlertSignal(QObject):
    alert_received = Signal(object)


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, event_bus):
        super().__init__()
        self.config = config
        self.bus = event_bus
        self.alert_signal = AlertSignal()
        self.alert_signal.alert_received.connect(self._on_alert_gui)

        self.setWindowTitle("E-SAG — Endpoint Security & Access Guard")
        self.resize(1200, 800)

        self._setup_menu()
        self._setup_tabs()
        self._setup_status_bar()
        self._subscribe_events()

        # Periodic refresh for process/network tables
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_monitors)
        self.refresh_timer.start(config.refresh_interval_sec * 1000)

    def _setup_menu(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        settings_menu = menubar.addMenu("&Settings")

        add_folder_action = QAction("Add Watched Folder", self)
        add_folder_action.triggered.connect(self._add_folder_dialog)
        file_menu.addAction(add_folder_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    def _setup_tabs(self) -> None:
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Dashboard tab
        self.dashboard = self._create_dashboard_tab()
        self.tabs.addTab(self.dashboard, "Dashboard")

        # Processes tab
        self.processes_tab = self._create_table_tab("Processes", ["PID", "Name", "CPU %", "Memory (MB)", "Path"])
        self.tabs.addTab(self.processes_tab, "Processes")

        # Network tab
        self.network_tab = self._create_table_tab("Network", ["PID", "Proto", "Local", "Remote", "Status"])
        self.tabs.addTab(self.network_tab, "Network")

        # File Events tab
        self.file_events_tab = self._create_table_tab("File Events", ["Time", "Type", "Path", "Dest", "Dir"])
        self.tabs.addTab(self.file_events_tab, "File Events")

        # Alerts tab
        self.alerts_tab = self._create_table_tab("Alerts", ["Time", "Severity", "Rule", "Message"])
        self.tabs.addTab(self.alerts_tab, "Alerts")

        # Settings tab
        self.settings_tab = self._create_settings_tab()
        self.tabs.addTab(self.settings_tab, "Settings")

    def _create_dashboard_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("E-SAG Dashboard — System Overview"))
        layout.addStretch()
        return widget

    def _create_table_tab(self, name: str, headers: list[str]) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        setattr(self, f"{name.lower().replace(' ', '_')}_table", table)
        layout.addWidget(table)
        return widget

    def _create_settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("Watched Folders"))
        self.folders_list = QTableWidget(0, 2)
        self.folders_list.setHorizontalHeaderLabels(["Path", "Action"])
        self.folders_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.folders_list)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Folder")
        add_btn.clicked.connect(self._add_folder_dialog)
        btn_layout.addWidget(add_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._refresh_folders_list()
        return widget

    def _setup_status_bar(self) -> None:
        self.statusBar().showMessage("E-SAG Ready")

    def _subscribe_events(self) -> None:
        self.bus.subscribe(FileCreatedEvent, lambda e: self.alert_signal.alert_received.emit(e))
        self.bus.subscribe(AlertEvent, lambda e: self.alert_signal.alert_received.emit(e))

    def _on_alert_gui(self, event) -> None:
        if isinstance(event, AlertEvent):
            self._add_alert_row(event)
        elif isinstance(event, FileCreatedEvent):
            self._add_file_event_row(event)

    def add_alert(self, event: AlertEvent) -> None:
        """Called from app_controller."""
        self.alert_signal.alert_received.emit(event)

    def _add_alert_row(self, event: AlertEvent) -> None:
        table = self.alerts_table
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(event.timestamp.strftime("%H:%M:%S")))
        table.setItem(row, 1, QTableWidgetItem(event.severity.value.upper()))
        table.setItem(row, 2, QTableWidgetItem(event.rule_name))
        table.setItem(row, 3, QTableWidgetItem(event.message))
        # Color by severity
        color = {"info": "#2196F3", "warning": "#FF9800", "critical": "#F44336"}.get(event.severity.value, "#000")
        for col in range(4):
            table.item(row, col).setForeground(Qt.GlobalColor(color))

    def _add_file_event_row(self, event: FileCreatedEvent) -> None:
        table = self.file_events_table
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(event.timestamp.strftime("%H:%M:%S")))
        table.setItem(row, 1, QTableWidgetItem(event.event_type.value))
        table.setItem(row, 2, QTableWidgetItem(str(event.path)))
        table.setItem(row, 3, QTableWidgetItem(str(event.dest_path) if event.dest_path else ""))
        table.setItem(row, 4, QTableWidgetItem("Yes" if event.is_directory else "No"))

    def _refresh_folders_list(self) -> None:
        table = self.folders_list
        table.setRowCount(0)
        for folder in self.config.watched_folders:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(str(folder)))
            remove_btn = QPushButton("Remove")
            remove_btn.clicked.connect(lambda _, p=folder: self._remove_folder(p))
            table.setCellWidget(row, 1, remove_btn)

    def _add_folder_dialog(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Watch")
        if folder:
            path = Path(folder)
            self.config = add_watched_folder(path, self.config)
            self._refresh_folders_list()
            # Restart monitoring for new folder
            from monitoring.file_monitor import start_folder
            start_folder(path)

    def _remove_folder(self, path: Path) -> None:
        self.config = remove_watched_folder(path, self.config)
        self._refresh_folders_list()
        from monitoring.file_monitor import stop_folder
        stop_folder(path)

    def _refresh_monitors(self) -> None:
        """Periodic refresh for process/network tables (TODO: implement psutil collection)."""
        self.statusBar().showMessage(f"Refreshed at {__import__('datetime').datetime.now().strftime('%H:%M:%S')}")

    def closeEvent(self, event) -> None:
        self.refresh_timer.stop()
        event.accept()