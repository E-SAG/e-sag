"""Event Bus for E-SAG. Pub/sub backbone — modules only talk through this."""
from collections import defaultdict
from threading import Lock
from typing import Callable, Any
from .types import BaseEvent


class EventBus:
    def __init__(self):
        self._subscribers: dict[type, list[Callable[[BaseEvent], None]]] = defaultdict(list)
        self._lock = Lock()
        self._event_history: list[BaseEvent] = []
        self._max_history = 1000

    def subscribe(self, event_type: type[BaseEvent], handler: Callable[[BaseEvent], None]) -> None:
        """Register handler for event type."""
        with self._lock:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: type[BaseEvent], handler: Callable[[BaseEvent], None]) -> None:
        """Remove handler for event type."""
        with self._lock:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)

    def emit(self, event: BaseEvent) -> None:
        """Emit event to all subscribers. Non-blocking."""
        with self._lock:
            handlers = self._subscribers.get(type(event), []).copy()
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"Event handler error: {e}")

    def get_recent(self, event_type: type[BaseEvent], limit: int = 50) -> list[BaseEvent]:
        """Get recent events of a type from history."""
        with self._lock:
            return [e for e in reversed(self._event_history) if isinstance(e, event_type)][:limit]


# Global singleton
bus = EventBus()