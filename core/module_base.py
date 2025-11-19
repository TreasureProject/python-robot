from abc import ABC, abstractmethod
from core.event_bus import EventBus

class ModuleBase(ABC):
    """
    Base class for all agent modules.
    Every module gets the event bus and implements start/stop/loop.
    """
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.running = False

    @abstractmethod
    async def start(self):
        """Initialize resources."""
        self.running = True

    @abstractmethod
    async def stop(self):
        """Clean up resources."""
        self.running = False

    @abstractmethod
    async def loop(self):
        """Module main loop."""
        pass
