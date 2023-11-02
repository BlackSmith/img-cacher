import json
import weakref
from typing import Callable

from aiohttp import web, WSMsgType, WSMessage
from aiohttp.web_request import Request
from loggate import get_logger


class SocketException(Exception): pass      # noqa


def socket_command(name: str):
    def wrap(fce):
        SocketManager.register_handlers(name, fce)
        return fce

    return wrap


async def pong(*args, **kwargs):
    return {'cmd': 'pong'}


class SocketManager:
    instance = None
    handlers = {
        'ping': pong
    }

    @classmethod
    def get(cls):
        return cls.instance

    @classmethod
    def register_handlers(cls, name: str, fce: Callable):
        if name in cls.handlers:
            raise SocketException(
                'The handler for this websocket call is already registered.')
        cls.handlers[name] = fce

    def __init__(self):
        if self.__class__.instance:
            raise SocketException('Multiple instances of SocketManager')
        self.sockets = weakref.WeakSet()
        self.logger = get_logger(self.__class__.__name__)
        self.__class__.instance = self

    async def websocket_handler(self, request: 'Request'):
        from .redis_manager import RedisManager
        db = RedisManager.get()
        ws: [WSMessage] = web.WebSocketResponse(heartbeat=10)
        self.sockets.add(ws)
        await ws.prepare(request)
        ws.remoteIP = request.remote
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                payload = json.loads(msg.data)
                cmd = payload.get('cmd')
                if cmd and (fce := self.handlers.get(cmd)):
                    if not fce:
                        continue
                    request_id = payload.get('requestId')
                    try:
                        res = await fce(payload, db=db, socket=ws)
                    except Exception as ex:
                        self.logger.error(str(ex), exc_info=ex)
                        res = {
                            'status': 'error',
                            'message': str(ex)
                        }
                    if not isinstance(res, dict):
                        res = {'payload': res}
                    if request_id and 'requestId' not in res:
                        res['requestId'] = request_id
                    await ws.send_json(res)
                else:
                    self.logger.error(
                        f'Unknown websocket handler "{payload}".')
            elif msg.type == WSMsgType.PING:
                print('PING')
            elif msg.type == WSMsgType.PONG:
                print('PONG')
            elif msg.type == WSMsgType.CLOSE:
                self.logger.info('WebSocket closed.')
                self.sockets.remove(ws)
            elif msg.type == WSMsgType.ERROR:
                self.logger.error(
                    f'WebSocket connection closed with exception'
                    f' {ws.exception()}')
                self.sockets.remove(ws)
        return ws

    async def publish(self, data):
        for ws in self.sockets:
            if not ws.closed:
                await ws.send_json(data)
