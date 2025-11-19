import asyncio
import os
import struct
from io import BytesIO
from core.module_base import ModuleBase

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai not available. Install with: pip install openai")


class OpenAIWhisperSTTModule(ModuleBase):
    """
    Speech-to-Text module using OpenAI Whisper API.
    
    Listens for 'audio_ready_for_stt' events and transcribes audio to text.
    Emits 'transcription' events with the transcribed text.
    """

    def __init__(self, event_bus, api_key=None, model="whisper-1"):
        super().__init__(event_bus)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.openai_client = None

    async def start(self):
        """Initialize OpenAI client."""
        if not OPENAI_AVAILABLE:
            raise RuntimeError("openai package is required but not installed")
        
        if not self.api_key:
            raise RuntimeError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.openai_client = AsyncOpenAI(api_key=self.api_key)
        self.running = True
        print("OpenAIWhisperSTTModule started.")

    async def stop(self):
        """Clean up resources."""
        self.running = False
        if self.openai_client:
            # OpenAI client doesn't need explicit cleanup
            self.openai_client = None
        print("OpenAIWhisperSTTModule stopped.")

    def _pcm_to_wav_bytesio(self, pcm_data: bytes, sample_rate: int, sample_width: int, channels: int) -> BytesIO:
        """
        Convert raw PCM bytes to WAV format in memory.
        Returns a BytesIO object containing the WAV file.
        """
        # WAV header constants
        byte_rate = sample_rate * sample_width * channels
        block_align = sample_width * channels
        data_size = len(pcm_data)
        file_size = 36 + data_size
        
        # Create WAV header
        wav_header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',                    # ChunkID
            file_size,                  # ChunkSize
            b'WAVE',                    # Format
            b'fmt ',                    # Subchunk1ID
            16,                         # Subchunk1Size (PCM)
            1,                          # AudioFormat (PCM)
            channels,                   # NumChannels
            sample_rate,                # SampleRate
            byte_rate,                  # ByteRate
            block_align,                # BlockAlign
            sample_width * 8,           # BitsPerSample
            b'data',                    # Subchunk2ID
            data_size                   # Subchunk2Size
        )
        
        # Combine header and PCM data
        wav_file = BytesIO()
        wav_file.write(wav_header)
        wav_file.write(pcm_data)
        wav_file.seek(0)  # Reset to beginning for reading
        
        return wav_file

    async def _transcribe_audio(self, audio_data: bytes, sample_rate: int, sample_width: int, channels: int) -> str:
        """
        Send audio to OpenAI Whisper API and return transcribed text.
        """
        if not self.openai_client:
            print("[STT] OpenAI client not available. Skipping transcription.")
            return None
        
        try:
            # Convert PCM to WAV in memory
            wav_file = self._pcm_to_wav_bytesio(audio_data, sample_rate, sample_width, channels)
            
            # OpenAI API expects a file-like object with a name attribute
            wav_file.seek(0)
            wav_file.name = "audio.wav"
            
            # Send to OpenAI Whisper API
            transcript = await self.openai_client.audio.transcriptions.create(
                model=self.model,
                file=wav_file,
                response_format="text"
            )
            
            return transcript.strip() if isinstance(transcript, str) and transcript else None
            
        except Exception as e:
            print(f"[STT ERROR] Failed to transcribe audio: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def loop(self):
        """Main loop: listen for audio_ready_for_stt events and transcribe."""
        while self.running:
            try:
                # Listen specifically for audio_ready_for_stt events
                event = await self.event_bus.listen("audio_ready_for_stt")
                payload = event.get("payload", {})
                
                audio_data = payload.get("audio_data")
                sample_rate = payload.get("sample_rate")
                sample_width = payload.get("sample_width")
                channels = payload.get("channels")
                audio_duration_sec = payload.get("audio_duration", 0)
                
                if not audio_data:
                    continue
                
                print(f"[STT] Received audio for transcription ({len(audio_data)} bytes, ~{audio_duration_sec:.2f}s)")
                print("[STT] Sending to Whisper API...")
                
                transcript = await self._transcribe_audio(audio_data, sample_rate, sample_width, channels)
                
                if transcript:
                    print(f"[STT] Transcription: {transcript}")
                    # Emit transcription event
                    await self.event_bus.emit("transcription", {
                        "text": transcript,
                        "audio_duration": audio_duration_sec,
                        "provider": "openai_whisper"
                    })
                else:
                    print("[STT] No transcription received")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[STT ERROR] Error in STT module loop: {e}")
                await asyncio.sleep(0.1)

