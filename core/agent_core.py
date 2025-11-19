# agent/core/agent_core.py

from typing import List
from core.event_bus import EventBus
from core.module_base import ModuleBase
from core.backend_connector import BackendConnector
import asyncio


class AgentCore:
    def __init__(self, modules: List[type[ModuleBase]], backend: BackendConnector, agent_name: str = None, sender_name: str = "User"):
        self.event_bus = EventBus()
        self.modules: List[ModuleBase] = [m(self.event_bus) for m in modules]
        self.backend = backend
        self.tasks = []
        self.agent_name = agent_name or "0xdacd02dd0ce8a923ad26d4c49bb94ece09306c3e"  # Default Wiz token ID
        self.sender_name = sender_name
        self.chat_history = []  # Store chat history for context

    async def start(self):
        print("Starting agent core...")

        for module in self.modules:
            await module.start()
            t = asyncio.create_task(module.loop())
            self.tasks.append(t)
        
        # Start event handler task
        event_handler_task = asyncio.create_task(self._event_handler_loop())
        self.tasks.append(event_handler_task)

    async def stop(self):
        print("Stopping agent core...")

        for m in self.modules:
            await m.stop()

        for t in self.tasks:
            t.cancel()

    async def _handle_transcription(self, text: str, payload: dict):
        """Handle transcription events by sending to chat API."""
        if not text or not text.strip():
            return
        
        try:
            print(f"[CHAT] Sending message to agent: '{text}'")
            
            # Send chat request
            result = await self.backend.chat(
                message=text,
                sender_name=self.sender_name,
                agent_name=self.agent_name,
                chat_history=self.chat_history,
            )
            
            # Update chat history
            self.chat_history.append({"role": "user", "content": text})
            
            # Handle response
            if result.get("response"):
                chat_response = result["response"]
                if "error" in chat_response:
                    print(f"[CHAT ERROR] {chat_response['error']}")
                elif "response" in chat_response:
                    agent_response = chat_response["response"]
                    print(f"[CHAT] Agent response: '{agent_response}'")
                    # Add agent response to history
                    self.chat_history.append({"role": "assistant", "content": agent_response})
                    # Emit event for TTS module
                    await self.event_bus.emit("agent_response", {
                        "text": agent_response
                    })
                else:
                    print(f"[CHAT] Unexpected response format: {chat_response}")
            
            # Log payment info if available
            if result.get("paymentResponse"):
                payment = result["paymentResponse"]
                print(f"[CHAT] Payment processed: {payment}")
                
        except Exception as e:
            error_msg = str(e)
            if "ReadTimeout" in error_msg or "timeout" in error_msg.lower():
                print(f"[CHAT ERROR] Request timed out. The server may be processing your request. Error: {error_msg}")
            elif "PaymentError" in error_msg:
                print(f"[CHAT ERROR] Payment processing error: {error_msg}")
            else:
                print(f"[CHAT ERROR] Failed to send chat request: {error_msg}")
            import traceback
            traceback.print_exc()

    async def _event_handler_loop(self):
        """Handle events from the event bus."""
        while True:
            try:
                event = await self.event_bus.listen()
                event_type = event.get("type")
                payload = event.get("payload", {})
                
                if event_type == "wake_word_detected":
                    print(f"[EVENT] Wake word detected! Payload: {payload}")
                
                elif event_type == "speech_start":
                    print(f"[EVENT] Speech started. Payload: {payload}")
                
                elif event_type == "audio_ready_for_stt":
                    audio_data = payload.get("audio_data")
                    sample_rate = payload.get("sample_rate")
                    sample_width = payload.get("sample_width")
                    channels = payload.get("channels")
                    audio_size_bytes = len(audio_data) if audio_data else 0
                    audio_duration_sec = (audio_size_bytes / (sample_rate * sample_width * channels)) if sample_rate and sample_width and channels else 0
                    
                    print(f"[EVENT] Audio ready for STT:")
                    print(f"  - Size: {audio_size_bytes} bytes")
                    print(f"  - Duration: ~{audio_duration_sec:.2f} seconds")
                    print(f"  - Sample rate: {sample_rate} Hz")
                    print(f"  - Sample width: {sample_width} bytes")
                    print(f"  - Channels: {channels}")
                    # STT modules will handle this event
                
                elif event_type == "transcription":
                    text = payload.get("text")
                    duration = payload.get("audio_duration", 0)
                    provider = payload.get("provider", "unknown")
                    print(f"[EVENT] Transcription received: '{text}' (duration: {duration:.2f}s, provider: {provider})")
                    # TODO: Process transcription - send to LLM, execute commands, etc.
                    await self._handle_transcription(text, payload)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ERROR] Event handler error: {e}")
                await asyncio.sleep(0.1)

    async def run(self):
        await self.start()
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await self.stop()
