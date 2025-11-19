from core.module_base import ModuleBase
from abc import ABC, abstractmethod

class SensorInputModule(ModuleBase, ABC):
    """
    Base class for generic sensor input modules.
    Examples: temperature, humidity, distance, button presses.
    """
    @abstractmethod
    async def read_sensor(self):
        """
        Read sensor value and emit events if needed.
        """
        pass
