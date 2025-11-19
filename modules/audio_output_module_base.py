from core.module_base import ModuleBase
from abc import ABC, abstractmethod

class AudioOutputModule(ModuleBase, ABC):
    """
    Base class for audio output modules (speakers, TTS, notifications)
    """
    @abstractmethod
    async def play_audio(self, data: bytes):
        """
        Play audio data through the output device.
        """
        pass
