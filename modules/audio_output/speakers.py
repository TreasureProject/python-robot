import asyncio
import pyaudio
from modules.audio_output_module_base import AudioOutputModule

class SpeakersModule(AudioOutputModule):
    """
    Plays audio data through the default speakers.
    Receives 'play_audio' commands via method call.
    """

    def __init__(self, event_bus, rate=16000):
        super().__init__(event_bus)
        self.rate = rate
        self.p = None
        self.stream = None

    async def start(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            output=True,
        )
        self.running = True
        print("SpeakersModule started.")

    async def stop(self):
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()
        print("SpeakersModule stopped.")

    async def loop(self):
        # Speakers just wait for commands; no loop needed
        while self.running:
            await asyncio.sleep(1)

    async def play_audio(self, data: bytes):
        if self.stream:
            self.stream.write(data)
