from core.module_base import ModuleBase
from abc import ABC, abstractmethod

class AudioInputModule(ModuleBase, ABC):
    """
    Base class for audio input modules (microphone, other audio sensors)
    """
    @abstractmethod
    async def process_audio_chunk(self, chunk: bytes):
        """
        Process a chunk of audio data.
        """
        pass
