

import sys
from pathlib import Path
from datetime import datetime
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Add the main E-SAG project folder to Python's import path
PROJECT_DIR = Path(__file__).resolve().parent.parent

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
from monitoring.folder_manager import (
    add_folder,
    remove_folder,
    get_monitored_folders,
)
# Import database functions
from database.database import create_database, insert_event

# Folder to monitor




PROJECT_DIR = Path(__file__).resolve().parent.parent
FOLDER_TO_WATCH = PROJECT_DIR / "test_watch"



class FileMonitorHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.recent_events = {}

    def record_event(self, event_type, event):
        # Filter repeated identical notifications
        event_key = (
            event_type,
            event.src_path,
            getattr(event, "dest_path", None),
            event.is_directory,
        )

        current_time = time.monotonic()
        previous_time = self.recent_events.get(event_key)

        if previous_time is not None:
            if current_time - previous_time < 0.75:
                print("Duplicate event ignored.")
                return

        self.recent_events[event_key] = current_time

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        source_path = event.src_path
        destination_path = getattr(
            event, "dest_path", None
        )

        # Save event to SQLite
        try:
            insert_event(
                timestamp,
                event_type,
                source_path,
                destination_path,
                event.is_directory
            )
            print("Event saved to database.")

        except Exception as error:
            print("Database error:", error)

       
        # Display event in terminal
        print("\n" + "=" * 55)
        print(f"[{timestamp}]  {event_type}")
        print("-" * 55)
        print(f"File/Folder : {source_path}")

        if destination_path:
            print(f"Moved to   : {destination_path}")

        print(f"Is folder  : {'Yes' if event.is_directory else 'No'}")
        print("=" * 55)


    def on_created(self, event):
        self.record_event("CREATED", event)

    def on_modified(self, event):
        self.record_event("MODIFIED", event)

    def on_deleted(self, event):
        self.record_event("DELETED", event)

    def on_moved(self, event):
        self.record_event("MOVED", event)

# Store active watchdog observers by folder path
ACTIVE_OBSERVERS = {}


def start_folder(folder_path):
    """Start monitoring a folder that is in the selected list."""

    folder = Path(folder_path).expanduser().resolve()

    if folder not in get_monitored_folders():
        print("Add this folder to the folder manager first.")
        return False

    if folder in ACTIVE_OBSERVERS:
        print("This folder is already being monitored.")
        return False

    observer = Observer()
    handler = FileMonitorHandler()

    observer.schedule(handler, str(folder), recursive=True)
    observer.start()

    ACTIVE_OBSERVERS[folder] = observer

    print("Monitoring started:", folder)
    return True


def stop_folder(folder_path):
    """Stop monitoring one folder."""

    folder = Path(folder_path).expanduser().resolve()
    observer = ACTIVE_OBSERVERS.get(folder)

    if observer is None:
        print("This folder is not currently monitored.")
        return False

    observer.stop()
    observer.join()

    del ACTIVE_OBSERVERS[folder]

    print("Monitoring stopped:", folder)
    return True


def start_all_folders():
    """Start monitoring all selected folders."""

    for folder in get_monitored_folders():
        start_folder(folder)


def stop_all_folders():
    """Stop every active observer."""

    for folder in list(ACTIVE_OBSERVERS.keys()):
        stop_folder(folder)



def start_monitoring():
    create_database()

   
    start_all_folders()

    print("\nE-SAG File Monitoring Started!")
    print("Commands:")
    print("  add <folder_path>    - Add and monitor a folder")
    print("  remove <folder_path> - Stop monitoring and remove a folder")
    print("  list                 - Show selected folders")
    print("  quit                 - Stop monitoring")

    try:
        while True:
            command = input("\nE-SAG> ").strip()

            if command.lower() == "quit":
                break

            elif command.lower() == "list":
                print("\nSelected folders:")
                for folder in get_monitored_folders():
                    print("-", folder)

            elif command.lower().startswith("add "):
                folder_path = command[4:].strip()

                if add_folder(folder_path):
                    start_folder(folder_path)

            elif command.lower().startswith("remove "):
                folder_path = command[7:].strip()

                stop_folder(folder_path)
                remove_folder(folder_path)

            else:
                print("Unknown command. Try add, remove, list, or quit.")

    except KeyboardInterrupt:
        print("\nStopping file monitoring...")

    finally:
        stop_all_folders()
        print("E-SAG monitoring stopped.")


if __name__ == "__main__":
    start_monitoring()



