"""Configuration for E-SAG. Loads from file, falls back to defaults."""
import json
from pathlib import Path
from .types import AppConfig


CONFIG_PATH = Path(__file__).parent.parent / "config.json"


DEFAULT_CONFIG = AppConfig(
    watched_folders=[],
    db_path=Path("database/file_events.db"),
    ml_model_path=Path("esag/ml/phishing_model.pkl"),
    refresh_interval_sec=5,
    alert_retention_days=30,
    max_events_in_memory=1000,
)


def load_config() -> AppConfig:
    """Load config from JSON, merge with defaults."""
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        watched = [Path(p) for p in data.get("watched_folders", [])]
        return AppConfig(
            watched_folders=watched,
            db_path=Path(data.get("db_path", str(DEFAULT_CONFIG.db_path))),
            ml_model_path=Path(data.get("ml_model_path", str(DEFAULT_CONFIG.ml_model_path))),
            refresh_interval_sec=data.get("refresh_interval_sec", DEFAULT_CONFIG.refresh_interval_sec),
            alert_retention_days=data.get("alert_retention_days", DEFAULT_CONFIG.alert_retention_days),
            max_events_in_memory=data.get("max_events_in_memory", DEFAULT_CONFIG.max_events_in_memory),
        )
    except Exception as e:
        print(f"Config load failed, using defaults: {e}")
        return DEFAULT_CONFIG


def save_config(config: AppConfig) -> None:
    """Save config to JSON."""
    data = {
        "watched_folders": [str(p) for p in config.watched_folders],
        "db_path": str(config.db_path),
        "ml_model_path": str(config.ml_model_path),
        "refresh_interval_sec": config.refresh_interval_sec,
        "alert_retention_days": config.alert_retention_days,
        "max_events_in_memory": config.max_events_in_memory,
    }
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def add_watched_folder(path: Path, config: AppConfig) -> AppConfig:
    """Return new config with folder added."""
    resolved = path.expanduser().resolve()
    if resolved not in config.watched_folders:
        config.watched_folders.append(resolved)
        save_config(config)
    return config


def remove_watched_folder(path: Path, config: AppConfig) -> AppConfig:
    """Return new config with folder removed."""
    resolved = path.expanduser().resolve()
    config.watched_folders = [p for p in config.watched_folders if p != resolved]
    save_config(config)
    return config