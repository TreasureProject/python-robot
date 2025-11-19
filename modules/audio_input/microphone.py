
import asyncio
import pyaudio
from modules.audio_input_module_base import AudioInputModule

class MicrophoneModule(AudioInputModule):
    """
    Captures audio from the default microphone and emits 'audio_chunk' events.
    """

    def __init__(self, event_bus, rate=16000, chunk_size=1024):
        super().__init__(event_bus)
        self.rate = rate
        self.chunk_size = chunk_size
        self.p = None
        self.stream = None

    async def start(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk_size,
        )
        self.running = True
        print("MicrophoneModule started.")

    async def stop(self):
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()
        print("MicrophoneModule stopped.")

    async def process_audio_chunk(self, chunk: bytes):
        """
        Process a chunk of audio data and emit it as an event.
        """
        await self.event_bus.emit("audio_chunk", {"chunk": chunk})

    async def loop(self):
        while self.running:
            chunk = self.stream.read(self.chunk_size, exception_on_overflow=False)
            await self.process_audio_chunk(chunk)
            await asyncio.sleep(0)  # yield control
