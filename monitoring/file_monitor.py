
import sys
from pathlib import Path
from datetime import datetime
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

# Project configuration
PROJECT_DIR = Path(__file__).resolve().parent.parent

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from monitoring.folder_manager import (
    add_folder,
    remove_folder,
    get_monitored_folders,
)

from database.database import (
    create_database,
    insert_event,
    count_events,
    get_recent_events,
)

console = Console()

FOLDER_TO_WATCH = PROJECT_DIR / "test_watch"

ACTIVE_OBSERVERS = {}


# Event colours
EVENT_STYLES = {
    "CREATED": "green",
    "MODIFIED": "yellow",
    "DELETED": "red",
    "MOVED": "cyan",
}


def show_banner():
    """Display the E-SAG startup banner."""

    banner = Text()
    banner.append("E-SAG\n", style="bold bright_cyan")
    banner.append(
        "ENDPOINT SECURITY & ACCESS GUARD",
        style="bold white"
    )

    console.print()
    console.print(
        Panel(
            banner,
            subtitle="[bold green]FILE MONITORING SYSTEM[/]",
            border_style="bright_cyan",
            padding=(1, 4),
        )
    )


def show_event(event_type, timestamp, source_path,
               destination_path, is_directory):
    """Display a formatted file-system event."""

    style = EVENT_STYLES.get(event_type, "white")

    table = Table(
        box=box.ROUNDED,
        show_header=False,
        border_style=style,
        expand=True,
    )

    table.add_column("Field", style="bold white", width=18)
    table.add_column(
        "Details",
        style="white",
        overflow="fold",
        no_wrap=False,
    )

    table.add_row("Time", timestamp)
    table.add_row("File / Folder", source_path)

    if destination_path:
        table.add_row("Moved to", destination_path)

    table.add_row(
        "Type",
        "Directory" if is_directory else "File"
    )

    console.print(
        Panel(
            table,
            title=f"[bold {style}] {event_type} [/]",
            border_style=style,
        )
    )
class FileMonitorHandler(FileSystemEventHandler):

    def __init__(self):
        super().__init__()
        self.recent_events = {}

    def record_event(self, event_type, event):

        event_key = (
            event_type,
            event.src_path,
            getattr(event, "dest_path", None),
            event.is_directory,
        )

        current_time = time.monotonic()
        previous_time = self.recent_events.get(event_key)

        # Ignore repeated identical notifications
        if previous_time is not None:
            if current_time - previous_time < 0.75:
                console.print(
                    "[dim yellow]Duplicate event ignored.[/]"
                )
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
                event.is_directory,
            )

            console.print(
                "[bold green]✓ Event saved to database[/]"
            )

        except Exception as error:
            console.print(
                f"[bold red]Database error: {error}[/]"
            )

        # Display formatted event
        show_event(
            event_type,
            timestamp,
            source_path,
            destination_path,
            event.is_directory,
        )

    def on_created(self, event):
        self.record_event("CREATED", event)

    def on_modified(self, event):
        self.record_event("MODIFIED", event)

    def on_deleted(self, event):
        self.record_event("DELETED", event)

    def on_moved(self, event):
        self.record_event("MOVED", event)


def start_folder(folder_path):
    """Start monitoring a saved folder."""

    folder = Path(folder_path).expanduser().resolve()

    if folder not in get_monitored_folders():
        console.print(
            "[bold red]✗ Add this folder to the folder manager first.[/]"
        )
        return False

    if folder in ACTIVE_OBSERVERS:
        console.print(
            "[yellow]This folder is already being monitored.[/]"
        )
        return False

    observer = Observer()
    handler = FileMonitorHandler()

    try:
        observer.schedule(handler, str(folder), recursive=True)
        observer.start()

    except Exception as error:
        console.print(
            f"[bold red]Could not start monitoring: {error}[/]"
        )
        return False

    ACTIVE_OBSERVERS[folder] = observer

    console.print(
        f"[bold green]✓ Monitoring started:[/] {folder}"
    )
    return True


def stop_folder(folder_path):
    """Stop monitoring one folder."""

    folder = Path(folder_path).expanduser().resolve()
    observer = ACTIVE_OBSERVERS.get(folder)

    if observer is None:
        console.print(
            "[yellow]This folder is not currently monitored.[/]"
        )
        return False

    observer.stop()
    observer.join()

    del ACTIVE_OBSERVERS[folder]

    console.print(
        f"[bold yellow]Monitoring stopped:[/] {folder}"
    )
    return True


def start_all_folders():
    """Start monitoring all saved folders."""

    for folder in get_monitored_folders():
        start_folder(folder)


def stop_all_folders():
    """Stop every active observer."""

    for folder in list(ACTIVE_OBSERVERS.keys()):
        stop_folder(folder)


def show_folders():
    """Display saved monitored folders in a table."""

    folders = get_monitored_folders()

    table = Table(
        title="E-SAG | Monitored Folders",
        box=box.ROUNDED,
        border_style="bright_cyan",
    )

    table.add_column("#", style="dim", justify="right")

    table.add_column(
        "Folder Path",
        style="white",
        overflow="fold",
        no_wrap=False,
    )

    table.add_column("Status", justify="center")

    for index, folder in enumerate(folders, start=1):
        active = folder in ACTIVE_OBSERVERS

        status = (
            "[bold green]ACTIVE[/]"
            if active
            else "[yellow]INACTIVE[/]"
        )

        table.add_row(str(index), str(folder), status)

    if not folders:
        table.add_row("-", "No folders saved", "-")

    console.print(table)
def show_commands():
    """Display available commands."""

    table = Table(
        title="Available Commands",
        box=box.SIMPLE,
        border_style="bright_cyan",
    )

    table.add_column("Command", style="bold cyan")
    table.add_column("Description", style="white")

    table.add_row("add <folder_path>", "Add and monitor a folder")
    table.add_row("remove <folder_path>", "Stop and remove a folder")
    table.add_row("list", "Show saved monitored folders")
    table.add_row("quit", "Stop the monitoring system")

    console.print(table)

def show_dashboard():
    """Display event statistics and recent activity."""

    total = count_events()
    recent_events = get_recent_events(5)

    console.print()

    stats = Table(
        title="E-SAG | SYSTEM OVERVIEW",
        box=box.ROUNDED,
        border_style="bright_cyan",
        expand=True,
    )

    stats.add_column("Metric", style="bold white")
    stats.add_column("Value", justify="center")

    stats.add_row(
        "Total recorded events",
        f"[bold bright_cyan]{total}[/]"
    )

    stats.add_row(
        "Recent events displayed",
        f"[bold green]{len(recent_events)}[/]"
    )

    console.print(stats)

    activity = Table(
        title="Recent File Activity",
        box=box.ROUNDED,
        border_style="bright_cyan",
        expand=True,
    )

    activity.add_column("Time", style="dim")
    activity.add_column("Event", style="bold")
    activity.add_column("File", overflow="fold")

    for event in recent_events:
        # Database row:
        # id, timestamp, event_type, source_path,
        # destination_path, is_directory

        timestamp = event[1]
        event_type = event[2]
        source = Path(event[3]).name
        destination = event[4]

        style = EVENT_STYLES.get(event_type, "white")

        filename = source

        if destination:
            filename += f" -> {Path(destination).name}"

        activity.add_row(
            timestamp,
            f"[{style}]{event_type}[/]",
            filename,
        )

    if not recent_events:
        activity.add_row("-", "No events yet", "-")

    console.print(activity)


def start_monitoring():

    create_database()
    start_all_folders()

    show_banner()
    show_dashboard()

    console.print(
        "\n[bold green]● E-SAG monitoring system is running[/]"
    )

    show_commands()

    try:
        while True:

            command = console.input(
                "\n[bold bright_cyan]E-SAG[/] [white]> [/]"
            ).strip()

            if command.lower() == "quit":
                break

            elif command.lower() == "list":
                show_folders()

            elif command.lower().startswith("add "):
                folder_path = command[4:].strip()

                if add_folder(folder_path):
                    start_folder(folder_path)

            elif command.lower().startswith("remove "):
                folder_path = command[7:].strip()

                stop_folder(folder_path)
                remove_folder(folder_path)

            else:
                console.print(
                    "[bold red]Unknown command.[/] "
                    "Use add, remove, list, or quit."
                )

    except KeyboardInterrupt:
        console.print(
            "\n[yellow]Stopping file monitoring...[/]"
        )

    finally:
        stop_all_folders()

        console.print(
            Panel(
                "[bold green]E-SAG monitoring stopped successfully.[/]",
                border_style="green",
            )
        )


if __name__ == "__main__":
    start_monitoring()
