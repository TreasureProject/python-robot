from core.module_base import ModuleBase
from abc import ABC, abstractmethod

class ActuatorModule(ModuleBase, ABC):
    """
    Base class for output/actuator modules.
    Examples: LEDs, motors, relays, displays.
    """
    @abstractmethod
    async def actuate(self, command: dict):
        """
        Execute an action based on a command dictionary.
        """
        pass
