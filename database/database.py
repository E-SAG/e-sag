
import sqlite3
from pathlib import Path


# Find the main E-SAG project folder
PROJECT_DIR = Path(__file__).resolve().parent.parent

# Database file location
DATABASE_PATH = PROJECT_DIR / "database" / "file_events.db"


def create_database():
    """Create the database and file_events table."""

    connection = sqlite3.connect(DATABASE_PATH)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            source_path TEXT NOT NULL,
            destination_path TEXT,
            is_directory INTEGER NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitored_folders (
            folder_path TEXT PRIMARY KEY,
            added_at TEXT NOT NULL
        )
    """)
    connection.commit()
    connection.close()

    print("Database and table created successfully!")


def insert_event(
    timestamp,
    event_type,
    source_path,
    destination_path,
    is_directory
):
    """Save one file-system event."""

    connection = sqlite3.connect(DATABASE_PATH)

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO file_events (
            timestamp,
            event_type,
            source_path,
            destination_path,
            is_directory
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        timestamp,
        event_type,
        source_path,
        destination_path,
        int(is_directory)
    ))

    connection.commit()
    connection.close()


def get_recent_events(limit=20):
    """Return the most recent file events."""

    connection = sqlite3.connect(DATABASE_PATH)

    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM file_events
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    events = cursor.fetchall()

    connection.close()

    return events


if __name__ == "__main__":
    create_database()


def get_events_by_type(event_type, limit=50):
    """Retrieve events matching a specific event type."""

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM file_events
        WHERE event_type = ?
        ORDER BY id DESC
        LIMIT ?
    """, (event_type.upper(), limit))

    events = cursor.fetchall()
    connection.close()

    return events


def search_events(path_keyword, limit=50):
    """Search event records using part of a file path."""

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM file_events
        WHERE source_path LIKE ?
           OR destination_path LIKE ?
        ORDER BY id DESC
        LIMIT ?
    """, (
        f"%{path_keyword}%",
        f"%{path_keyword}%",
        limit
    ))

    events = cursor.fetchall()
    connection.close()

    return events



def clear_event_history(confirm=False):
    """Clear event history only after explicit confirmation."""

    if not confirm:
        print("History was not cleared.")
        print("Call clear_event_history(confirm=True) to confirm.")
        return

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("DELETE FROM file_events")

    connection.commit()
    connection.close()

    print("Event history cleared.")


from datetime import datetime, timedelta


def count_events():
    """Return the number of stored file events."""

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM file_events")
    total = cursor.fetchone()[0]

    connection.close()

    return total


def delete_events_older_than(days):
    """Delete event records older than the specified number of days."""

    if days < 0:
        raise ValueError("Days cannot be negative.")

    cutoff_date = datetime.now() - timedelta(days=days)
    cutoff_text = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM file_events
        WHERE timestamp < ?
    """, (cutoff_text,))

    deleted_count = cursor.rowcount

    connection.commit()
    connection.close()

    print(f"Deleted {deleted_count} old event records.")
    return deleted_count

def save_monitored_folder(folder_path):
    """Save a folder path in the database."""

    folder_path = str(Path(folder_path).expanduser().resolve())

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO monitored_folders (folder_path, added_at)
            VALUES (?, ?)
        """, (
            folder_path,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        connection.commit()
        return True

    except sqlite3.IntegrityError:
        # This folder path is already saved
        return False

    finally:
        connection.close()


def delete_monitored_folder(folder_path):
    """Remove a saved folder path from the database."""

    folder_path = str(Path(folder_path).expanduser().resolve())

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM monitored_folders
        WHERE folder_path = ?
    """, (folder_path,))

    removed = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return removed


def load_monitored_folders():
    """Return saved folder paths."""

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT folder_path
        FROM monitored_folders
        ORDER BY folder_path
    """)

    folders = [Path(row[0]) for row in cursor.fetchall()]

    connection.close()

    return folders
