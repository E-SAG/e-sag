
from pathlib import Path

from database.database import (
    create_database,
    save_monitored_folder,
    delete_monitored_folder,
    load_monitored_folders,
)


def add_folder(folder_path):
    """Validate and permanently save a folder."""

    folder = Path(folder_path).expanduser().resolve()

    if not folder.exists():
        print("Error: This folder does not exist.")
        return False

    if not folder.is_dir():
        print("Error: The selected path is not a folder.")
        return False

    create_database()

    saved = save_monitored_folder(folder)

    if not saved:
        print("This folder is already saved.")
        return False

    print("Folder added:", folder)
    return True


def remove_folder(folder_path):
    """Remove a folder from the saved list."""

    folder = Path(folder_path).expanduser().resolve()

    removed = delete_monitored_folder(folder)

    if not removed:
        print("This folder is not in the saved list.")
        return False

    print("Folder removed:", folder)
    return True



def get_monitored_folders():
    """Return saved folders that currently exist."""

    folders = load_monitored_folders()
    valid_folders = []

    for folder in folders:
        if folder.exists() and folder.is_dir():
            valid_folders.append(folder)
        else:
            print("Saved folder is currently unavailable:", folder)

    return sorted(valid_folders)
