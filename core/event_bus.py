import asyncio
from typing import Any, Dict, List, Optional

class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}
        self.default_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

    async def emit(self, event_type: str, payload: Any = None):
        """Emit an event to all subscribers of this event type."""
        event = {"type": event_type, "payload": payload}
        
        # Send to specific subscribers
        if event_type in self.subscribers:
            for queue in self.subscribers[event_type]:
                await queue.put(event)
        
        # Also send to default queue for backward compatibility
        await self.default_queue.put(event)

    async def listen(self, event_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Listen for events. If event_type is specified, only receives that event type.
        Otherwise, receives all events (backward compatible).
        """
        if event_type:
            # Subscribe to specific event type
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            queue = asyncio.Queue()
            self.subscribers[event_type].append(queue)
            return await queue.get()
        else:
            # Default: listen to all events (backward compatible)
            return await self.default_queue.get()
