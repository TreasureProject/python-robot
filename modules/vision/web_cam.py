import cv2
import asyncio
from modules.vision_module_base import VisionModule

class WebCamModule(VisionModule):
    """
    Captures frames from the webcam and emits 'frame' events.
    """

    def __init__(self, event_bus, device_index=0):
        super().__init__(event_bus)
        self.device_index = device_index
        self.cap = None

    async def start(self):
        self.cap = cv2.VideoCapture(self.device_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open webcam {self.device_index}")
        self.running = True
        print("WebCamModule started.")

    async def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        print("WebCamModule stopped.")

    async def process_frame(self, frame):
        """
        Process a single video frame and emit it as an event.
        """
        await self.event_bus.emit("frame", {"frame": frame})

    async def loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                await self.process_frame(frame)
            await asyncio.sleep(0.01)  # small delay to avoid CPU hogging
