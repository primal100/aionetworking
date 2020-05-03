import asyncio
from aionetworking.actions.base import BaseAction
from aionetworking.types.formats import MessageObjectType
from dataclasses import dataclass, field
from aionetworking.factories import queue_defaultdict

from typing import AsyncGenerator, DefaultDict


class InvalidRequestError(Exception):
    pass


@dataclass
class EchoAction(BaseAction):
    supports_notifications = True
    _queues: DefaultDict[str, asyncio.Queue] = field(default_factory=queue_defaultdict, init=False, compare=False, repr=False)

    async def get_notifications(self, peer: str) -> AsyncGenerator[None, None]:
        queue = self._queues[peer]
        while True:
            item = await queue.get()
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
            self._queues[msg.full_sender].put_nowait('notification')
        elif method == 'simple':
            pass
        else:
            raise InvalidRequestError(f'{method} is not recognised as a valid method')
