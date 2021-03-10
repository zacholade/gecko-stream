import asyncio
from aiohttp import web
from cv2 import VideoCapture, flip, resize, imencode

from mixins import LoggingMixin, ConfigMixin


class WebServer(ConfigMixin, LoggingMixin):
    def __init__(self) -> None:
        self.app = web.Application()
        self.app.router.add_get("/", self.handle_index)
        self.runner = None

        self._stream = VideoCapture(self.config.VIDEO_STREAM_URL)
        if not self._stream.isOpened():
            raise RuntimeError('Cannot open camera')

    async def start(self) -> None:
        """
        Run the server asynchronously.
        """
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, 'localhost', self.config.WEB_SERVER_PORT)
        await site.start()

    async def handle_index(self, request) -> web.StreamResponse:
        """
        Called when "/" is called.
        """
        response = web.StreamResponse()
        response.content_type = 'multipart/x-mixed-replace; boundary=frame'
        await response.prepare(request)

        for frame in self.frames():
            await response.write(frame)
        return response

    def frames(self):
        while True:
            _, img = self._stream.read()
            img = flip(resize(img, (1920, 1080)), 0)
            frame = imencode('.jpg', img)[1].tobytes()
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'


server = WebServer()
loop = asyncio.get_event_loop()
loop.create_task(server.start())
loop.run_forever()

