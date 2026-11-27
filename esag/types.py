"""Shared types for E-SAG. Single source of truth for all event dataclasses."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class EventType(Enum):
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    FILE_MOVED = "file_moved"
    PROCESS_STARTED = "process_started"
    PROCESS_STOPPED = "process_stopped"
    NETWORK_CONNECTION = "network_connection"
    ALERT = "alert"
    PHISHING_CHECK = "phishing_check"


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class BaseEvent:
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""  # module that emitted (e.g., "file_monitor", "process_monitor")


@dataclass
class FileEvent(BaseEvent):
    path: Path = field(default_factory=Path)
    dest_path: Optional[Path] = None
    is_directory: bool = False

    def __post_init__(self):
        self.event_type = EventType.FILE_CREATED  # overridden by subclasses


@dataclass
class FileCreatedEvent(FileEvent):
    def __post_init__(self):
        self.event_type = EventType.FILE_CREATED


@dataclass
class FileModifiedEvent(FileEvent):
    def __post_init__(self):
        self.event_type = EventType.FILE_MODIFIED


@dataclass
class FileDeletedEvent(FileEvent):
    def __post_init__(self):
        self.event_type = EventType.FILE_DELETED


@dataclass
class FileMovedEvent(FileEvent):
    dest_path: Path

    def __post_init__(self):
        self.event_type = EventType.FILE_MOVED


@dataclass
class ProcessEvent(BaseEvent):
    pid: int = 0
    name: str = ""
    exe_path: Optional[Path] = None
    cpu_percent: float = 0.0
    memory_mb: float = 0.0


@dataclass
class ProcessStartedEvent(ProcessEvent):
    def __post_init__(self):
        self.event_type = EventType.PROCESS_STARTED


@dataclass
class ProcessStoppedEvent(ProcessEvent):
    def __post_init__(self):
        self.event_type = EventType.PROCESS_STOPPED


@dataclass
class NetworkEvent(BaseEvent):
    pid: int = 0
    local_addr: str = ""
    local_port: int = 0
    remote_addr: str = ""
    remote_port: int = 0
    status: str = ""
    proto: str = "tcp"

    def __post_init__(self):
        self.event_type = EventType.NETWORK_CONNECTION


@dataclass
class AlertEvent(BaseEvent):
    rule_name: str = ""
    severity: AlertSeverity = AlertSeverity.INFO
    message: str = ""
    details: dict = field(default_factory=dict)

    def __post_init__(self):
        self.event_type = EventType.ALERT


@dataclass
class PhishingCheckEvent(BaseEvent):
    url: str = ""
    is_phishing: bool = False
    confidence: float = 0.0

    def __post_init__(self):
        self.event_type = EventType.PHISHING_CHECK


@dataclass
class MonitoredFolder:
    path: Path
    added_at: datetime
    active: bool = True


@dataclass
class AppConfig:
    watched_folders: list[Path] = field(default_factory=list)
    db_path: Path = Path("database/file_events.db")
    ml_model_path: Path = Path("esag/ml/phishing_model.pkl")
    refresh_interval_sec: int = 5
    alert_retention_days: int = 30
    max_events_in_memory: int = 1000