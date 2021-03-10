import asyncio
from aiohttp import web
import cv2

from mixins import LoggingMixin, ConfigMixin


class WebServer(ConfigMixin, LoggingMixin):
    def __init__(self, camera_stream_url: str) -> None:
        self.app = web.Application()
        self.app.router.add_get("/", self.handle_index)
        self.runner = None

        self._stream = cv2.VideoCapture(camera_stream_url)
        self._video_stream_url = self.config.VIDEO_STREAM_URL

    async def start(self) -> None:
        """
        Run the server asynchronously.
        """
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, 'localhost', self.config.WEB_SERVER_PORT)
        await site.start()

    async def handle_index(self, request):
        """
        Called when "/" is called.
        """
        response = web.StreamResponse()
        response.content_type = 'multipart/x-mixed-replace; boundary=frame'
        await response.prepare(request)

        for frame in self.frames(self._video_stream_url):
            await response.write(frame)
        return response

    def frames(self, path):
        camera = cv2.VideoCapture(path)
        if not camera.isOpened():
            raise RuntimeError('Cannot open camera')

        while True:
            _, img = camera.read()
            img = cv2.flip(cv2.resize(img, (1920, 1080)), 0)
            frame = cv2.imencode('.jpg', img)[1].tobytes()
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'


server = WebServer("http://192.168.0.93:12345")
loop = asyncio.get_event_loop()
loop.create_task(server.start())
loop.run_forever()

