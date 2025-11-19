from core.module_base import ModuleBase
from abc import ABC, abstractmethod

class VisionModule(ModuleBase, ABC):
    """
    Base class for vision-related modules.
    Examples: camera, face detection, motion detection.
    """
    @abstractmethod
    async def process_frame(self, frame):
        """
        Process a single video frame.
        """
        pass
