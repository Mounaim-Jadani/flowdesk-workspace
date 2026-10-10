"""Small in-process event bus for Karma integrations.

Existing features emit domain events through :func:`emit_karma` instead of
depending directly on Karma's scoring implementation. The scoring handlers
will be added in the next Karma subtasks.
"""

from collections.abc import Callable
from typing import Any


KarmaHandler = Callable[..., Any]
KARMA_EVENT_HANDLERS: dict[str, KarmaHandler] = {}


def register_karma_event(kind: str) -> Callable[[KarmaHandler], KarmaHandler]:
    """Register the decorated function as the handler for an event kind.

    One handler is intentionally kept per event kind. This keeps the first
    bus version deterministic while allowing the implementation behind each
    event to evolve independently from chat and checklist code.
    """

    if not kind or not kind.strip():
        raise ValueError('Karma event kind must not be empty.')

    normalized_kind = kind.strip()

    def decorator(handler: KarmaHandler) -> KarmaHandler:
        if not callable(handler):
            raise TypeError('Karma event handler must be callable.')
        KARMA_EVENT_HANDLERS[normalized_kind] = handler
        return handler

    return decorator


def emit_karma(kind: str, **context: Any) -> Any:
    """Dispatch a Karma event to its registered handler.

    Unknown event kinds are intentionally ignored. This allows existing
    features to emit an event safely before its scoring rule is deployed.
    Handler exceptions are not swallowed: callers must see implementation
    failures instead of silently losing Karma events.
    """

    handler = KARMA_EVENT_HANDLERS.get(kind)
    if handler is None:
        return None
    return handler(**context)
