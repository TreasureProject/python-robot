from core.module_base import ModuleBase
from abc import ABC, abstractmethod

class AIModule(ModuleBase, ABC):
    """
    Base class for AI-related modules.
    Examples: TTS, wake word detection, speech recognition, LLM integration, etc.
    Can receive input from other modules via event bus.
    """
    
    @abstractmethod
    async def handle_audio_chunk(self, chunk: bytes):
        """
        Handle audio chunk input from audio input modules.
        """
        pass
    
    @abstractmethod
    async def handle_frame(self, frame):
        """
        Handle video frame input from vision modules.
        """
        pass
    
    @abstractmethod
    async def handle_text(self, text: str):
        """
        Handle text input (e.g., for TTS, LLM processing).
        """
        pass

