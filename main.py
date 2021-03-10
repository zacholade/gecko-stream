import asyncio
import logging
import os

from typing import Union
from aiohttp import web
import cv2

from mixins import LoggingMixin, ConfigMixin

logger = logging.getLogger(__name__)


class WebServer(ConfigMixin, LoggingMixin):
    def __init__(self) -> None:
        self.app = web.Application()
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/live", self.handle_live)
        self.app.router.add_get("/videos", self.handle_videos)
        self.runner = None

    async def start(self) -> None:
        """
        Run the server asynchronously.
        """
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', self.config.WEB_SERVER_PORT)
        self.logger.info("Running!")
        await site.start()

    async def handle_index(self, request) -> web.Response:
        """
        Called when "/" is called.
        """
        return web.HTTPFound('/videos')

    async def handle_videos(self, request) -> Union[web.Response, web.StreamResponse]:
        """
        Called when /videos is called.
        If a ?video=id is specified, we try to stream that video if exists.
        """
        video = request.rel_url.query.get('video')
        if video:
            response = web.StreamResponse()
            response.content_type = 'multipart/x-mixed-replace; boundary=frame'
            await response.prepare(request)
            for frame in self._get_frames("videos/" + video):
                await response.write(frame)
            return response

        # This is blocking. But for our purpose this is fine.
        files = [file for file in os.listdir("./videos") if file.endswith('.mp4')]
        html = '<h1>Watch Finn Live:</h1><a href="/live">Live Link</a><h1>All Videos:</h1>'
        for file in files:
            html += f'<a href="/videos?video={file}">{file}</a><br>'
        return web.Response(body=html, content_type="text/html")

    async def handle_live(self, request) -> web.StreamResponse:
        """
        Called when "/live" is called.
        """
        response = web.StreamResponse()
        response.content_type = 'multipart/x-mixed-replace; boundary=frame'
        await response.prepare(request)

        for frame in self._get_frames(self.config.VIDEO_STREAM_URL, flip=True):
            await response.write(frame)
        return response

    def _get_frames(self, path, flip=False):
        video = cv2.VideoCapture(path)
        if not video.isOpened():
            raise RuntimeError('Cannot connect to video stream.')

        while True:
            _, img = video.read()
            img = cv2.resize(img, (1920, 1080))
            if flip:
                img = cv2.flip(img, 0)
            frame = cv2.imencode('.jpg', img)[1].tobytes()
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'


server = WebServer()
loop = asyncio.get_event_loop()
loop.create_task(server.start())
loop.run_forever()

