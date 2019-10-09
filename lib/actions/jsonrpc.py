from __future__ import annotations
import asyncio
from dataclasses import dataclass, field, InitVar
from functools import wraps

from lib.actions.base import BaseAction
from lib.formats.contrib.types import JSONObjectType
from lib.networking.connections_manager import connections_manager

from typing import Any, Dict, AnyStr, NoReturn, Tuple


class MethodNotFoundError(BaseException):
    pass


class InvalidParamsError(BaseException):
    pass


class InvalidRequestError(BaseException):
    pass


@dataclass
class JSONRPCServer(BaseAction):
    app_cls: Any = None
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

    def __post_init__(self) -> None:
        self.app = self.app_cls(notifications_queue=self._notifications_queue)

    async def start(self) -> None:
        await self.app.start()
        self.task = asyncio.create_task(self.manage_queue())

    async def close(self) -> None:
        await self.app.close()
        await self._notifications_queue.join()
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

    async def do_one(self, msg: JSONObjectType) -> Dict[str, Any]:
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

    def on_decode_error(self, data: AnyStr, exc: BaseException) -> Dict:
        return {"jsonrpc": self.version, "error": self.exception_codes.get('ParseError')}

    def _get_exception_details(self, exc: BaseException):
        exc_name = exc.__class__.__name__
        error = self.app.exception_codes.get(exc_name, None)
        if error:
            error['message'] = str(exc) or error['message']
        else:
            error = self.exception_codes.get(exc_name, self.exception_codes['InvalidRequestError'])
        return error

    def on_exception(self, msg_obj: JSONObjectType, exc: BaseException) -> Dict[str, Any]:
        request_id = msg_obj.get('id', None)
        error = self._get_exception_details(exc)
        return {"jsonrpc": self.version, "error": error, "id": request_id}


@dataclass
class BaseJSONRPCApp:
    exception_codes = {}
    is_requester = False
    conn = None
    notifications_queue: asyncio.Queue

    async def start_for_server(self): ...

    def set_requester(self, conn: ConnectionProtocol):
        self.is_requester = True
        self.conn = conn

    async def close(self):
        if self.conn:
            await self.conn.close_wait()


class BaseJSONRPCMethod:
    version = "2.0"
    name = ''
    request_id = None

    def _get_rpc_command(self, *args, **kwargs) -> Dict[str, Any]:
        command = {"jsonrpc": self.version, "method": self.name}
        if self.request_id is not None:
            command['id'] = self.request_id
        if args:
            command['params'] = args
        elif kwargs:
            command['params'] = kwargs
        return command


class JSONRPCMethod(BaseJSONRPCMethod):
    request_id = 0

    def __init__(self, conn: ConnectionProtocol, name: str):
        self.conn = conn
        JSONRPCMethod.request_id += 1
        self.request_id = JSONRPCMethod.request_id
        self.name = name

    async def __call__(self, *args, **kwargs):
        command = self._get_rpc_command(*args, **kwargs)
        return await self.conn.encode_send_wait(command)


class JSONRPCMethodNotification(BaseJSONRPCMethod):
    version = "2.0"

    def __init__(self, conn: ConnectionProtocol, name: str):
        self.conn = conn
        self.name = name

    def __call__(self, *args, **kwargs):
        command = self._get_rpc_command(*args, **kwargs)
        return self.conn.encode_and_send_msg(command)


def rpc_method(f):
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if self.is_requester:
            method = JSONRPCMethod(self.conn, f.__name__)
            return method(*args, **kwargs)
        return f(*args, **kwargs)
    return wrapper


def rpc_method_notification(f):
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if self.is_requester:
            method = JSONRPCMethodNotification(self.conn, f.__name__)
            return method(*args, **kwargs)
        return f(*args, **kwargs)
    return wrapper
