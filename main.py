import os
import asyncio
from dotenv import load_dotenv

from core.agent_core import AgentCore
from core.backend_connector import BackendConnector
from modules.vision.web_cam import WebCamModule
from modules.audio_input.wake_word_vad import WakeWordVADModule
from modules.audio_output.speakers import SpeakersModule
from modules.ai.openai_whisper_stt import OpenAIWhisperSTTModule
from modules.ai.elevenlabs_tts import ElevenLabsTTSModule

load_dotenv()
BACKEND_URL = "https://aifrens.lol/paid";
MNEMONIC = os.getenv("MNEMONIC")
AGENT_NAME = os.getenv("AGENT_NAME", "0xdacd02dd0ce8a923ad26d4c49bb94ece09306c3e")  # Default Wiz token ID
SENDER_NAME = os.getenv("SENDER_NAME", "User")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

backend = BackendConnector(
    base_url=BACKEND_URL,
    x402_mnemonic=MNEMONIC
)
# Factory function for ElevenLabsTTSModule with voice_id
def create_elevenlabs_tts(voice_id):
    def factory(event_bus):
        return ElevenLabsTTSModule(event_bus, voice_id=voice_id)
    return factory

modules = [
    WebCamModule,
    WakeWordVADModule,  # Simple multi-criteria VAD (RMS + ZCR + spectral centroid)
    OpenAIWhisperSTTModule,
    create_elevenlabs_tts(ELEVENLABS_VOICE_ID),  # TTS with ElevenLabs
    SpeakersModule
]
print("Initializing agent core...")
core = AgentCore(modules=modules, backend=backend, agent_name=AGENT_NAME, sender_name=SENDER_NAME)
print("Agent core initialized.")

async def main():
    print("Starting agent core (no modules yet)...")
    await core.run()

if __name__ == "__main__":
    asyncio.run(main())