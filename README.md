# Python Robot - Voice Assistant Agent

A modular Python-based voice assistant robot that uses AI for speech-to-text, natural language processing, and text-to-speech. The agent integrates with a backend API using x402 payment protocol for AI interactions.

## Features

- 🎤 **Voice Activity Detection (VAD)**: Automatically detects when you're speaking using multi-criteria analysis (RMS energy, zero-crossing rate, spectral centroid)
- 🗣️ **Speech-to-Text**: Transcribes your speech using OpenAI Whisper API
- 🤖 **AI Chat Integration**: Sends transcriptions to an AI backend API with x402 payment protocol support
- 🔊 **Text-to-Speech**: Converts AI responses to natural-sounding speech using ElevenLabs
- 📹 **Webcam Support**: Vision module for camera input (extensible)
- 🔌 **Modular Architecture**: Event-driven system with pluggable modules

## Architecture

The project uses an event-driven architecture with the following components:

```
┌─────────────────┐
│   AgentCore     │  ← Main orchestrator
└────────┬────────┘
         │
    ┌────┴────┐
    │EventBus │  ← Event communication hub
    └────┬────┘
         │
    ┌────┴─────────────────────────────┐
    │                                   │
┌───▼──────────┐  ┌──────────────┐  ┌──▼────────────┐
│ WakeWordVAD  │  │ OpenAIWhisper│  │ ElevenLabsTTS │
│   Module     │─▶│    STT       │─▶│    Module     │
└──────────────┘  └──────────────┘  └───────────────┘
    │                    │                    │
    │                    │                    │
    ▼                    ▼                    ▼
Microphone         Transcription         Speakers
```

### Event Flow

1. **WakeWordVADModule** continuously listens for speech
2. When speech is detected, it records audio until silence
3. Emits `audio_ready_for_stt` event with audio data
4. **OpenAIWhisperSTTModule** receives audio and transcribes it
5. Emits `transcription` event with text
6. **AgentCore** handles transcription and sends to backend API
7. Backend responds with AI-generated text
8. **AgentCore** emits `agent_response` event
9. **ElevenLabsTTSModule** converts text to speech and plays it

## Installation

### Prerequisites

- Python 3.8 or higher
- Microphone and speakers/headphones
- API keys for:
  - OpenAI (for Whisper STT)
  - ElevenLabs (for TTS)
  - Backend API access

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Create a `.env` file in the project root:

```env
# Required: x402 payment mnemonic (seed phrase)
MNEMONIC=your twelve word seed phrase here

# Required: OpenAI API key for speech-to-text
OPENAI_API_KEY=sk-your-openai-api-key

# Required: ElevenLabs API key and voice ID for text-to-speech
ELEVENLABS_API_KEY=your-elevenlabs-api-key
ELEVENLABS_VOICE_ID=your-voice-id

# Optional: Agent configuration
AGENT_NAME=0xdacd02dd0ce8a923ad26d4c49bb94ece09306c3e  # Default Wiz token ID
SENDER_NAME=User
```

## Usage

### Basic Usage

Run the agent:

```bash
python main.py
```

The agent will:
1. Initialize all modules
2. List available audio input devices
3. Start listening for speech
4. Process your voice input and respond with AI-generated speech

### Stopping the Agent

Press `Ctrl+C` to gracefully stop the agent and all modules.

## Configuration

### Audio Input Device

By default, the agent uses the system's default microphone. To specify a different device:

1. Run the agent once to see available devices
2. Edit `modules/audio_input/wake_word_vad.py` and set `device_index` in the `WakeWordVADModule` constructor

Example:
```python
WakeWordVADModule(
    event_bus,
    device_index=2,  # Use device index 2
    rate=16000,
    chunk_size=512,
    vad_threshold=0.01,
    silence_timeout_ms=1000
)
```

### VAD Sensitivity

Adjust voice activity detection sensitivity in `main.py`:

```python
WakeWordVADModule(
    event_bus,
    vad_threshold=0.01,      # Lower = more sensitive (0.005-0.02)
    silence_timeout_ms=1000  # Milliseconds of silence before ending speech
)
```

### ElevenLabs Voice

Change the voice by updating `ELEVENLABS_VOICE_ID` in your `.env` file. You can find available voices in your ElevenLabs dashboard.

## Modules

### Core Modules

- **AgentCore** (`core/agent_core.py`): Main orchestrator that manages modules and handles events
- **EventBus** (`core/event_bus.py`): Event-driven communication system
- **BackendConnector** (`core/backend_connector.py`): Handles HTTP requests and x402 payments
- **ModuleBase** (`core/module_base.py`): Base class for all modules

### Audio Input Modules

- **WakeWordVADModule** (`modules/audio_input/wake_word_vad.py`): Voice activity detection using multi-criteria analysis
- **MicrophoneModule** (`modules/audio_input/microphone.py`): Basic microphone input (if needed)

### AI Modules

- **OpenAIWhisperSTTModule** (`modules/ai/openai_whisper_stt.py`): Speech-to-text using OpenAI Whisper API
- **ElevenLabsTTSModule** (`modules/ai/elevenlabs_tts.py`): Text-to-speech using ElevenLabs API

### Audio Output Modules

- **SpeakersModule** (`modules/audio_output/speakers.py`): Audio playback through speakers

### Vision Modules

- **WebCamModule** (`modules/vision/web_cam.py`): Webcam input (extensible for future use)

## Extending the Agent

### Creating a New Module

1. Create a new file in the appropriate module directory
2. Inherit from `ModuleBase` or a more specific base class
3. Implement required methods: `start()`, `stop()`, `loop()`
4. Use `event_bus.emit()` to send events
5. Use `event_bus.listen()` to receive events
6. Add your module to the `modules` list in `main.py`

Example:

```python
from core.module_base import ModuleBase

class MyModule(ModuleBase):
    async def start(self):
        self.running = True
        print("MyModule started")
    
    async def stop(self):
        self.running = False
        print("MyModule stopped")
    
    async def loop(self):
        while self.running:
            event = await self.event_bus.listen("my_event_type")
            # Process event...
            await asyncio.sleep(0.1)
```

## Troubleshooting

### Audio Issues

**Problem**: No audio input detected
- Check microphone permissions
- Verify device index is correct
- Ensure microphone is not muted
- Try adjusting `vad_threshold` (lower = more sensitive)

**Problem**: Audio playback not working
- Check speakers/headphones are connected
- Verify audio output device in system settings

### API Issues

**Problem**: OpenAI API errors
- Verify `OPENAI_API_KEY` is set correctly
- Check API key has sufficient credits
- Ensure internet connection is stable

**Problem**: ElevenLabs API errors
- Verify `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` are set
- Check API key has sufficient credits
- Verify voice ID exists in your account

**Problem**: Backend connection errors
- Verify `BACKEND_URL` is correct
- Check backend server is running
- Ensure `MNEMONIC` is set for x402 payments
- Check network connectivity

## Project Structure

```
python-robot/
├── core/                    # Core system components
│   ├── agent_core.py       # Main orchestrator
│   ├── backend_connector.py # API and payment handling
│   ├── event_bus.py        # Event system
│   └── module_base.py      # Base module class
├── modules/                 # Pluggable modules
│   ├── ai/                 # AI services (STT, TTS)
│   ├── audio_input/        # Audio input modules
│   ├── audio_output/       # Audio output modules
│   └── vision/             # Vision modules
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Dependencies

- `eth-account`: Ethereum account management for x402 payments
- `x402`: x402 payment protocol client
- `python-dotenv`: Environment variable management
- `opencv-python`: Computer vision (for webcam)
- `pyaudio`: Audio I/O
- `numpy`: Numerical operations
- `openai`: OpenAI API client (Whisper)
- `elevenlabs`: ElevenLabs API client (TTS)

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions, please [open an issue on GitHub] or contact [your contact information].

