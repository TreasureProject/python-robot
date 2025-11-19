from typing import Any
import asyncio
import pyaudio
import numpy as np
from collections import deque
from modules.audio_input_module_base import AudioInputModule


class WakeWordVADModule(AudioInputModule):
    """
    Voice Activity Detection (VAD) module using multi-criteria approach.
    
    Pipeline:
    1. Continuously listens for speech using VAD (RMS energy + ZCR + spectral centroid)
    2. When speech detected, starts recording
    3. Collects audio while speech is active
    4. When speech ends (silence timeout), sends full audio to STT backend via event
    """

    def __init__(
        self,
        event_bus,
        device_index=2,
        rate=16000,
        chunk_size=512,
        vad_threshold=0.01,  # RMS energy threshold
        silence_timeout_ms=1000,
        debug_audio_levels=False,  # Only log when speech detected
    ):
        super().__init__(event_bus)
        self.device_index = device_index  # None = default device
        self.rate = rate
        self.chunk_size = chunk_size
        self.vad_threshold = vad_threshold
        self.silence_timeout_ms = silence_timeout_ms
        self.debug_audio_levels = debug_audio_levels
        
        # Audio setup
        self.p = None
        self.stream = None
        
        # State management
        self.speech_buffer = deque(maxlen=int(rate * 10))  # Max 10 seconds
        self.last_speech_time = None
        self.speech_detected = False
        
        # VAD processing buffer - accumulate audio for better VAD accuracy
        self.vad_buffer = deque[Any](maxlen=int(rate * 0.1))  # 100ms buffer
        
        # Audio format
        self.sample_width = 2  # 16-bit = 2 bytes
        self.channels = 1

    async def start(self):
        """Initialize audio stream."""
        
        # Initialize PyAudio
        self.p = pyaudio.PyAudio()
        
        # List available audio input devices
        print("\n=== Available Audio Input Devices ===")
        input_devices = []
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                input_devices.append((i, info))
                default_marker = " (DEFAULT)" if i == self.p.get_default_input_device_info()['index'] else ""
                print(f"  [{i}] {info['name']} - {info['maxInputChannels']} channels, {int(info['defaultSampleRate'])} Hz{default_marker}")
        print("=====================================\n")
        
        # Select device
        if self.device_index is None:
            self.device_index = self.p.get_default_input_device_info()['index']
            print(f"Using default input device: [{self.device_index}] {self.p.get_device_info_by_index(self.device_index)['name']}")
        else:
            device_info = self.p.get_device_info_by_index(self.device_index)
            print(f"Using specified input device: [{self.device_index}] {device_info['name']}")
        
        # Open audio stream
        try:
            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to open audio stream on device {self.device_index}: {e}")
        
        self.running = True
        print(f"WakeWordVADModule started. Listening for speech (RMS threshold: {self.vad_threshold})...")

    async def stop(self):
        """Clean up resources."""
        self.running = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()
        
        print("WakeWordVADModule stopped.")

    def _process_audio_chunk_for_vad(self, audio_data: bytes) -> bool:
        """
        Process audio chunk using multi-criteria VAD (RMS energy + ZCR + spectral centroid).
        Returns True if speech detected.
        Based on the C++ implementation provided.
        """
        try:
            # Convert bytes to int16 array
            pcm = np.frombuffer(audio_data, dtype=np.int16)
            
            if len(pcm) == 0:
                return False
            
            # Calculate audio level for debugging
            audio_level = np.abs(pcm).mean()
            max_level = np.abs(pcm).max()
            
            # 1. Calculate RMS energy
            normalized = pcm.astype(np.float32) / 32768.0
            rms_energy = np.sqrt(np.mean(normalized ** 2))
            
            # 2. Calculate zero-crossing rate (ZCR)
            zero_crossings = np.sum((pcm[1:] >= 0) != (pcm[:-1] < 0))
            zcr = float(zero_crossings) / (len(pcm) - 1) if len(pcm) > 1 else 0.0
            
            # 3. Calculate spectral centroid (simplified)
            spectral_centroid = 0.0
            if len(pcm) > 1:
                # Simple magnitude calculation (treating pairs as complex)
                magnitudes = []
                for i in range(0, len(pcm) - 1, 2):
                    real = pcm[i] / 32768.0
                    imag = pcm[i + 1] / 32768.0
                    magnitudes.append(np.sqrt(real * real + imag * imag))
                
                if len(magnitudes) > 0:
                    sum_mag = np.sum(magnitudes)
                    if sum_mag > 0.0:
                        for i, mag in enumerate(magnitudes):
                            spectral_centroid += (i * mag) / sum_mag
            
            # Multi-criteria decision making - require 2 out of 3 criteria (less strict)
            energy_ok = rms_energy > self.vad_threshold
            zcr_ok = 0.1 < zcr < 0.5  # Wider ZCR range for speech
            spectral_ok = spectral_centroid > 0.1  # Lower spectral content requirement
            
            criteria_met = sum([energy_ok, zcr_ok, spectral_ok])
            is_speech = criteria_met >= 2  # Require at least 2 out of 3
            
            # Log when speech is detected OR when there's significant audio but not detected (for debugging)
            if is_speech:
                print(f"🎤 Speech detected! RMS={rms_energy:.4f} ZCR={zcr:.3f} Spectral={spectral_centroid:.3f} (E:{energy_ok} Z:{zcr_ok} S:{spectral_ok})")
            elif rms_energy > 0.005:  # Log when there's audio but not detected (temporary debugging)
                print(f"[DEBUG] Audio but no speech: RMS={rms_energy:.4f} ZCR={zcr:.3f} Spectral={spectral_centroid:.3f} (E:{energy_ok} Z:{zcr_ok} S:{spectral_ok})")
            
            return is_speech
        except Exception as e:
            print(f"VAD processing error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _handle_speech_start(self):
        """Handle speech start detection."""
        if not self.speech_detected:
            self.speech_detected = True
            print("🎤 Speech detected, recording...")
            await self.event_bus.emit("speech_start", {})

    async def _handle_speech_end(self):
        """Handle speech end - send full audio to STT backend."""
        if len(self.speech_buffer) > 0:
            # Convert deque to numpy array, then to bytes
            audio_array = np.array(list(self.speech_buffer), dtype=np.int16)
            audio_bytes = audio_array.tobytes()
            
            print(f"✅ Speech ended. Sending {len(audio_bytes)} bytes to STT backend...")
            await self.event_bus.emit("audio_ready_for_stt", {
                "audio_data": audio_bytes,
                "sample_rate": self.rate,
                "sample_width": self.sample_width,
                "channels": self.channels,
            })
            
            # Reset state
            self.speech_buffer.clear()
            self.speech_detected = False
            self.last_speech_time = None

    async def process_audio_chunk(self, chunk: bytes):
        """
        Process audio chunk: use VAD to detect speech start/stop.
        Accumulates audio into larger windows for better VAD accuracy.
        """
        import time
        current_time = time.time() * 1000  # milliseconds
        
        # Convert chunk to int16 array
        pcm = np.frombuffer(chunk, dtype=np.int16)
        
        # Always add to speech buffer (for recording)
        self.speech_buffer.extend(pcm)
        
        # Accumulate into VAD buffer and process
        self.vad_buffer.extend(pcm)
        
        # Process VAD on every chunk for responsiveness
        is_speech = False
        # Use current chunk + accumulated buffer for better accuracy
        vad_samples = np.array(list(self.vad_buffer), dtype=np.int16)
        if len(vad_samples) > 0:
            vad_audio = vad_samples.tobytes()
            is_speech = self._process_audio_chunk_for_vad(vad_audio)
        
        if is_speech:
            await self._handle_speech_start()
            self.last_speech_time = current_time
        else:
            # Check if we've had enough silence to end speech
            if self.speech_detected and self.last_speech_time:
                silence_duration = current_time - self.last_speech_time
                if silence_duration >= self.silence_timeout_ms:
                    await self._handle_speech_end()
                    return

    async def loop(self):
        """Main loop: continuously read audio and process it."""
        while self.running:
            try:
                # Read audio chunk
                chunk = self.stream.read(self.chunk_size, exception_on_overflow=False)
                await self.process_audio_chunk(chunk)
                await asyncio.sleep(0)  # Yield control
            except Exception as e:
                print(f"Error in WakeWordVADModule loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(0.1)

