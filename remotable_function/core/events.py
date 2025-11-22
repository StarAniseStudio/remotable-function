"""
Event System for Remotable

A unified, priority-based event system with support for:
- Priority-based event handlers
- Unsubscribe functionality
- Sync and async callbacks
- Event handler lifecycle management
"""

import asyncio
import logging
from typing import Callable, Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import IntEnum


logger = logging.getLogger(__name__)


class EventPriority(IntEnum):
    """Event handler priority levels"""

    LOWEST = 0
    LOW = 25
    NORMAL = 50
    HIGH = 75
    HIGHEST = 100


@dataclass
class EventHandler:
    """Event handler with priority and metadata"""

    callback: Callable
    priority: int = EventPriority.NORMAL
    once: bool = False  # If True, handler will be removed after first execution
    handler_id: Optional[str] = None  # Unique ID for this handler
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Generate handler_id if not provided"""
        if self.handler_id is None:
            self.handler_id = f"{id(self.callback)}_{id(self)}"


class EventEmitter:
    """
    Event emitter with priority and unsubscribe support.

    Features:
    - Priority-based handler execution
    - Sync and async callback support
    - Unsubscribe functionality
    - One-time handlers
    - Handler metadata
    """

    def __init__(self):
        """Initialize event emitter"""
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._handler_map: Dict[str, EventHandler] = {}  # For unsubscribe by ID

    def on(
        self,
        event: str,
        callback: Callable,
        priority: int = EventPriority.NORMAL,
        once: bool = False,
        handler_id: Optional[str] = None,
        **metadata,
    ) -> str:
        """
        Register event handler.

        Args:
            event: Event name
            callback: Handler function (sync or async)
            priority: Handler priority (higher = executed first)
            once: If True, handler will be removed after first execution
            handler_id: Optional unique ID for this handler
            **metadata: Additional metadata for this handler

        Returns:
            handler_id: Unique ID for this handler (for unsubscribe)

        Example:
            # Simple handler
            emitter.on("connected", lambda: print("Connected!"))

            # High priority handler
            emitter.on("connected", handler, priority=EventPriority.HIGH)

            # One-time handler
            handler_id = emitter.on("connected", handler, once=True)

            # Handler with metadata
            emitter.on("data", handler, timeout=5, max_retries=3)
        """
        handler = EventHandler(
            callback=callback,
            priority=priority,
            once=once,
            handler_id=handler_id,
            metadata=metadata,
        )

        # Add to event handlers list
        if event not in self._handlers:
            self._handlers[event] = []

        self._handlers[event].append(handler)

        # Sort by priority (highest first)
        self._handlers[event].sort(key=lambda h: h.priority, reverse=True)

        # Add to handler map for unsubscribe
        self._handler_map[handler.handler_id] = handler

        logger.debug(
            f"Registered handler {handler.handler_id} for event '{event}' "
            f"(priority={priority}, once={once})"
        )

        return handler.handler_id

    def once(
        self,
        event: str,
        callback: Callable,
        priority: int = EventPriority.NORMAL,
        **metadata,
    ) -> str:
        """
        Register one-time event handler.

        Convenience method for on(event, callback, once=True).

        Args:
            event: Event name
            callback: Handler function
            priority: Handler priority
            **metadata: Additional metadata

        Returns:
            handler_id: Unique ID for this handler
        """
        return self.on(event, callback, priority=priority, once=True, **metadata)

    def off(self, event: Optional[str] = None, handler_id: Optional[str] = None) -> int:
        """
        Unsubscribe event handler(s).

        Args:
            event: Event name (if None, removes all handlers for handler_id)
            handler_id: Handler ID (if None, removes all handlers for event)

        Returns:
            Number of handlers removed

        Examples:
            # Remove specific handler
            emitter.off(handler_id="my_handler_123")

            # Remove all handlers for an event
            emitter.off(event="connected")

            # Remove specific handler from specific event
            emitter.off(event="connected", handler_id="my_handler_123")
        """
        removed_count = 0

        if handler_id is not None:
            # Remove specific handler
            if handler_id in self._handler_map:
                handler = self._handler_map[handler_id]

                # Find and remove from event handlers
                for evt, handlers in self._handlers.items():
                    if event is None or evt == event:
                        try:
                            handlers.remove(handler)
                            removed_count += 1
                            logger.debug(f"Removed handler {handler_id} from event '{evt}'")
                        except ValueError:
                            pass

                # Remove from handler map
                del self._handler_map[handler_id]

        elif event is not None:
            # Remove all handlers for an event
            if event in self._handlers:
                removed_count = len(self._handlers[event])

                # Remove from handler map
                for handler in self._handlers[event]:
                    if handler.handler_id in self._handler_map:
                        del self._handler_map[handler.handler_id]

                self._handlers[event] = []
                logger.debug(f"Removed all handlers for event '{event}' (count={removed_count})")

        else:
            logger.warning("off() called with neither event nor handler_id")

        return removed_count

    async def emit(self, event: str, *args, **kwargs) -> None:
        """
        Emit event to all registered handlers.

        Handlers are executed in priority order (highest priority first).
        Supports both sync and async handlers.

        Args:
            event: Event name
            *args: Positional arguments for handlers
            **kwargs: Keyword arguments for handlers

        Example:
            await emitter.emit("connected", client_id="123")
        """
        if event not in self._handlers:
            return

        handlers_to_remove = []

        for handler in self._handlers[event][:]:  # Copy list to avoid modification during iteration
            try:
                # Execute handler
                if asyncio.iscoroutinefunction(handler.callback):
                    await handler.callback(*args, **kwargs)
                else:
                    handler.callback(*args, **kwargs)

                # Mark one-time handlers for removal
                if handler.once:
                    handlers_to_remove.append(handler)

            except Exception as e:
                logger.error(
                    f"Error in handler {handler.handler_id} for event '{event}': {e}",
                    exc_info=True,
                )

        # Remove one-time handlers
        for handler in handlers_to_remove:
            self.off(event=event, handler_id=handler.handler_id)

    def list_handlers(self, event: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        List registered handlers.

        Args:
            event: Event name (if None, lists all events)

        Returns:
            Dictionary mapping event names to handler info lists

        Example:
            handlers = emitter.list_handlers("connected")
            # {
            #     "connected": [
            #         {"handler_id": "...", "priority": 50, "once": False},
            #         ...
            #     ]
            # }
        """
        result = {}

        events = [event] if event else self._handlers.keys()

        for evt in events:
            if evt in self._handlers:
                result[evt] = [
                    {
                        "handler_id": h.handler_id,
                        "priority": h.priority,
                        "once": h.once,
                        "is_async": asyncio.iscoroutinefunction(h.callback),
                        "metadata": h.metadata,
                    }
                    for h in self._handlers[evt]
                ]

        return result

    def clear(self) -> None:
        """Clear all event handlers."""
        count = sum(len(handlers) for handlers in self._handlers.values())
        self._handlers.clear()
        self._handler_map.clear()
        logger.debug(f"Cleared all event handlers (count={count})")
