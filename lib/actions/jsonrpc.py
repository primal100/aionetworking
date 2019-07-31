from __future__ import annotations
import asyncio
from dataclasses import dataclass, field, InitVar

from lib.actions.base import BaseAction
from lib.formats.contrib.types import JSONObjectType
from lib.networking.network_connections import connections_manager, ConnectionsManager

from typing import Any, Dict, AnyStr, NoReturn, Tuple


class MethodNotFoundError(BaseException):
    pass


class InvalidParamsError(BaseException):
    pass


class InvalidRequestError(BaseException):
    pass


@dataclass
class JSONRPCServer(BaseAction):
    app: Any = None
    version = '2.0'
    exception_codes = {
        'InvalidRequestError': {"code": -32600, "message": "Invalid Request"},
        'MethodNotFoundError': {"code": -32601, "message": "Method not found"},
        'InvalidParamsError': {"code": -32602, "message": "Invalid params"},
        'InternalError': {"code": -32603, "message": "Invalid params"},
        'ParseError': {"code": -32700, "message": "Parse error"}
    }
    _notifications_queue: asyncio.Queue[Tuple[str, Any]] = field(default_factory=asyncio.Queue, init=False)
    task: asyncio.Task = field(default=None, init=False)
    start_task: InitVar[bool] = True

    def __post_init__(self, start_task) -> None:
        if start_task:
            self.task = asyncio.create_task(self.manage_queue())

    async def close(self) -> None:
        if hasattr(self.app, 'close_app'):
            await self.app.close_app()
        await asyncio.wait((super().close(), self._notifications_queue.join()), timeout=self.timeout)
        if self.task:
            self.task.cancel()

    def create_notification(self, result: Any):
        return {'jsonrpc': self.version, 'result': result}

    async def manage_queue(self):
        while True:
            key, result = await self._notifications_queue.get()
            try:
                item = self.create_notification(result)
                self.logger.debug('Sending notification for key %s', key)
                connections_manager.notify(key, item)
            finally:
                self._notifications_queue.task_done()

    @staticmethod
    def _raise_correct_exception(exc: BaseException) -> NoReturn:
        if "positional argument" or "keyword argument" in str(exc):
            raise InvalidParamsError
        raise exc

    async def asnyc_do_one(self, msg: JSONObjectType) -> Dict[str, Any]:
        try:
            if msg['jsonrpc'] != self.version:
                raise InvalidRequestError
        except KeyError:
            raise InvalidRequestError
        request_id = msg.request_id
        try:
            func = getattr(self.app, msg['method'])
        except KeyError:
            raise InvalidRequestError
        except AttributeError:
            raise MethodNotFoundError
        params = msg.get('params')
        try:
            if isinstance(params, (tuple, list)):
                result = await func(msg, self._notifications_queue, *params)
            elif isinstance(params, dict):
                result = await func(msg, self._notifications_queue, **params)
            else:
                result = await func(msg, self._notifications_queue)
            if request_id is not None:
                return {'jsonrpc': self.version, 'result': result, 'id': request_id}
        except TypeError as exc:
            self._raise_correct_exception(exc)

    def response_on_decode_error(self, data: AnyStr, exc: BaseException) -> Dict:
        return {"jsonrpc": self.version, "error": self.exception_codes.get('ParseError')}

    def _get_exception_details(self, exc: BaseException):
        exc_name = exc.__class__.__name__
        error = getattr(self.app, 'exception_codes', {}).get(exc_name, None)
        if error:
            error['message'] = str(exc) or error['message']
        else:
            error = self.exception_codes.get(exc_name, self.exception_codes['InvalidRequestError'])
        return error

    def response_on_exception(self, msg_obj: JSONObjectType, exc: BaseException) -> Dict[str, Any]:
        request_id = msg_obj.get('id', None)
        error = self._get_exception_details(exc)
        return {"jsonrpc": self.version, "error": error, "id": request_id}
