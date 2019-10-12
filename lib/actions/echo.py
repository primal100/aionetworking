import asyncio
from lib.actions.base import BaseAction
from lib.formats.types import MessageObjectType
from dataclasses import dataclass, field

from typing import AsyncGenerator


class InvalidRequestError(BaseException):
    pass


@dataclass
class EchoAction(BaseAction):
    supports_notifications = True
    _queue: asyncio.Queue = field(default_factory=asyncio.Queue, init=False, compare=False, repr=False)

    async def get_notifications(self) -> AsyncGenerator[None, None]:
        while True:
            item = await self._queue.get()
            yield {'result': item}

    def on_decode_error(self, data: bytes, exc: BaseException) -> dict:
        return {'error': 'JSON was invalid'}

    def on_exception(self, msg: MessageObjectType, exc: BaseException) -> dict:
        return {'id': msg.decoded['id'], 'error': exc.__class__.__name__}

    async def do_one(self, msg: MessageObjectType) -> dict:
        method = msg.decoded['method']
        if method == 'echo':
            id_ = msg.decoded.get('id')
            return {'id': id_, 'result': 'echo'}
        elif method == 'send_notification':
            self._queue.put_nowait('notification')
        else:
            raise InvalidRequestError(f'{method} is not recognised as a valid method')
