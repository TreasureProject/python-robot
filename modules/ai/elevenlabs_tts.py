import asyncio
import os
import pyaudio
import subprocess
from io import BytesIO
from typing import Tuple, Optional
from core.module_base import ModuleBase
from elevenlabs import AsyncElevenLabs

class ElevenLabsTTSModule(ModuleBase):
    """
    Text-to-Speech module using ElevenLabs API.
    
    Listens for 'agent_response' events and converts text to speech,
    then plays it through the speakers.
    """

    def __init__(self, event_bus, api_key=None, voice_id=None, model="eleven_multilingual_v2"):
        super().__init__(event_bus)
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID")
        self.model = model
        self.client = None
        self.p = None
        self.stream = None
        self.sample_rate = 44100  # Default for mp3_44100_128 format

    async def start(self):
        """Initialize ElevenLabs client and audio output."""
        if not self.api_key:
            raise RuntimeError("ElevenLabs API key is required. Set ELEVENLABS_API_KEY environment variable or pass api_key parameter.")
        
        if not self.voice_id:
            raise RuntimeError("ElevenLabs voice ID is required. Set ELEVENLABS_VOICE_ID environment variable or pass voice_id parameter.")
        
        # Initialize async ElevenLabs client
        self.client = AsyncElevenLabs(api_key=self.api_key)
        
        # Initialize PyAudio for audio playback (will be opened when needed with correct sample rate)
        self.p = pyaudio.PyAudio()
        self.stream = None  # Will be opened when we know the sample rate
        
        self.running = True
        print(f"ElevenLabsTTSModule started (voice_id: {self.voice_id}, model: {self.model})")

    async def stop(self):
        """Clean up resources."""
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()
        print("ElevenLabsTTSModule stopped.")

    async def _text_to_speech(self, text: str) -> Tuple[Optional[bytes], Optional[int]]:
        """
        Convert text to speech using ElevenLabs API.
        Returns (audio_data as PCM bytes, sample_rate).
        """
        if not self.client or not self.voice_id:
            print("[TTS] Client or voice ID not set. Skipping TTS.")
            return None, None
        
        try:
            # Generate audio using ElevenLabs async client
            # Using mp3_44100_128 format for good quality
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id=self.model,
                output_format="mp3_44100_128"
            )
            
            # Convert async generator to bytes (MP3 format)
            mp3_bytes = b""
            async for chunk in audio_generator:
                mp3_bytes += chunk
            
            # Convert MP3 to PCM using ffmpeg
            # ffmpeg -i input.mp3 -f s16le -acodec pcm_s16le -ar 44100 -ac 1 output.raw
            process = await asyncio.create_subprocess_exec(
                'ffmpeg',
                '-i', 'pipe:0',  # Read from stdin
                '-f', 's16le',   # 16-bit signed little-endian PCM
                '-acodec', 'pcm_s16le',
                '-ar', '44100',  # Sample rate
                '-ac', '1',      # Mono
                'pipe:1',        # Write to stdout
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            
            stdout, _ = await process.communicate(input=mp3_bytes)
            
            if process.returncode != 0:
                raise RuntimeError(f"ffmpeg conversion failed with return code {process.returncode}")
            
            return stdout, 44100
            
        except FileNotFoundError:
            print("[TTS ERROR] ffmpeg not found. Please install ffmpeg to use TTS.")
            return None, None
        except Exception as e:
            print(f"[TTS ERROR] Failed to generate speech: {e}")
            import traceback
            traceback.print_exc()
            return None, None

    async def _play_audio(self, audio_data: bytes, sample_rate: int):
        """Play audio data through speakers."""
        if not audio_data or not sample_rate:
            return
        
        try:
            # Close existing stream if sample rate changed
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            
            # Open stream with correct sample rate
            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                output=True,
            )
            
            # Play audio in chunks
            chunk_size = 1024
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                self.stream.write(chunk)
            
            # Wait for playback to finish
            self.stream.stop_stream()
            
        except Exception as e:
            print(f"[TTS ERROR] Failed to play audio: {e}")
            import traceback
            traceback.print_exc()

    async def loop(self):
        """Main loop: listen for agent_response events and convert to speech."""
        while self.running:
            try:
                # Listen specifically for agent_response events
                event = await self.event_bus.listen("agent_response")
                payload = event.get("payload", {})
                
                text = payload.get("text")
                
                if not text or not text.strip():
                    continue
                
                print(f"[TTS] Converting to speech: '{text[:50]}...'")
                
                # Convert text to speech
                audio_data, sample_rate = await self._text_to_speech(text)
                
                if audio_data and sample_rate:
                    print(f"[TTS] Playing audio ({len(audio_data)} bytes, {sample_rate} Hz)...")
                    await self._play_audio(audio_data, sample_rate)
                    print("[TTS] Audio playback complete")
                else:
                    print("[TTS] No audio generated")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[TTS ERROR] Error in TTS module loop: {e}")
                await asyncio.sleep(0.1)

