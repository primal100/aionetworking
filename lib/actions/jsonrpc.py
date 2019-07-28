from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
import secrets

from lib.actions.base import BaseAction
from lib.formats.contrib.types import JSONObjectType
from lib.networking.network_connections import connections_manager

from typing import Any, Dict, List, AnyStr, NoReturn


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
    _notifications_queue: asyncio.Queue = field(default_factory=asyncio.Queue, init=False)

    def __post_init__(self) -> None:
        self.task = asyncio.create_task(self.manage_queue())

    async def close(self) -> None:
        await asyncio.wait((super().close(), self._notifications_queue.join()))
        self.task.cancel()
        await self.task

    async def manage_queue(self):
        while True:
            key, result = await self._notifications_queue.get()
            item = {'jsonrpc': self.version, 'result': result}
            self.logger.debug('Sending notification for key %s', key)
            connections_manager.notify(key, item)
            self._notifications_queue.task_done()

    @staticmethod
    def raise_correct_exception(exc: Exception) -> NoReturn:
        if "positional argument" or "keyword argument" in str(exc):
            raise InvalidParamsError
        raise exc

    async def async_do_one(self, msg: JSONObjectType) -> Dict[str, Any]:
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
                result = await func(msg)
            if request_id is not None:
                return {'jsonrpc': self.version, 'result': result, 'id': request_id}
        except TypeError as exc:
            self.raise_correct_exception(exc)

    def response_on_decode_error(self, data: AnyStr, exc: BaseException) -> Dict:
        return {"jsonrpc": self.version, "error": self.exception_codes.get('ParseError')}

    def get_exception_details(self, exc: BaseException):
        exc_name = exc.__class__.__name__
        error = getattr(self.app, 'exception_codes', {}).get(exc_name, None)
        if error:
            error['message'] = str(exc) or error['message']
        else:
            error = self.exception_codes.get(exc_name, self.exception_codes['InvalidRequestError'])
        return error

    def response_on_exception(self, msg_obj: JSONObjectType, exc: Exception) -> Dict[str, Any]:
        request_id = msg_obj.get('id', None)
        error = self.get_exception_details(exc)
        return {"jsonrpc": self.version, "error": error, "id": request_id}


class AuthenticationError(BaseException):
    pass


class PermissionsError(BaseException):
    pass


class InvalidSessionIDError(BaseException):
    pass


class ObjectNotFoundError(BaseException):
    pass


@dataclass
class SampleJSONRPCServer:
    session_id_length: int = 16
    users: Dict[str, Dict] = field(default_factory=dict)
    notes: Dict[int, Dict] = field(default_factory=dict)
    last_id: int = 0

    exception_codes = {
        'AuthenticationError': {"code": -30000, "message": "Login failed"},
        'PermissionsError': {"code": -30001, "message": "You do not have permissions to perform this action"},
        'InvalidSessionIDError': {"code": -30002, "message": "Wrong session id for this user"},
        'KeyError': {"code": -31000, "message": "That object does not exist"},
    }

    def add_user(self, user: str, password: str):
        self.users[user] = {'user': user, 'password': password}

    def delete_user(self, user: str):
        del self.users[user]

    def check_session_id(self, user: str, session_id: str):
        try:
            if not self.users[user]['session_id'] == session_id:
                raise InvalidSessionIDError
            return user
        except KeyError:
            raise AuthenticationError

    def check_user(self, msg_obj: JSONObjectType):
        user = msg_obj.context['user']
        if user in self.users:
            return user
        raise AuthenticationError

    def generate_session_id(self):
        return secrets.token_urlsafe(self.session_id_length)

    def check_owner(self, user: str, object_id: int, ):
        return self.notes[object_id]['user'] == user

    async def login(self, msg_obj: JSONObjectType, queue: asyncio.Queue, user: str = None, password: str = None):
        try:
            user = self.users[user]
        except KeyError:
            raise AuthenticationError
        if user['password'] == password:
            session_id = self.generate_session_id()
            user['session_id'] = session_id
            msg_obj.context['user'] = user
            return {'user': user, 'session_id': session_id, 'message': 'Login successful'}
        raise AuthenticationError

    async def authenticate(self, msg_obj: JSONObjectType, queue: asyncio.Queue, user: str, session_id: str):
        self.check_session_id(user, session_id)
        msg_obj.context['user'] = user
        return {'user': user, 'session_id': session_id, 'message': 'Authentication successful'}

    async def logout(self, msg_obj: JSONObjectType, queue: asyncio.Queue):
        user = msg_obj.context['user']
        msg_obj.context['user'] = None
        del self.users[user]['session_id']
        return {'user': user, 'message': 'Logout successful'}

    async def create(self, msg_obj: JSONObjectType, queue: asyncio.Queue, name: str = None, text: str = None) -> Dict:
        user = self.check_user(msg_obj)
        if not name:
            raise InvalidParamsError
        self.last_id += 1
        note = {'id': self.last_id, 'name': name, 'text': text, 'user': user}
        self.notes[self.last_id] = note
        result = {'id': note['id'], 'message': 'New note has been created', 'user': user}
        await queue.put((f"user_{user}", result))
        return result

    async def delete(self, msg_obj: JSONObjectType, queue: asyncio.Queue, object_id: int = None) -> Dict:
        user = self.check_user(msg_obj)
        if not object_id:
            raise InvalidParamsError
        self.check_owner(user, object_id)
        del self.notes[object_id]
        result = {'id': object_id, 'message': 'Note has been deleted', 'user': user}
        await queue.put((f"user_{user}", result))
        return result

    async def get(self, msg_obj: JSONObjectType, queue: asyncio.Queue, object_id: int = None) -> Dict:
        if not object_id:
            raise InvalidParamsError
        return self.notes[object_id]

    async def update(self, msg_obj: JSONObjectType, queue: asyncio.Queue, object_id: int = None, **params) -> Dict:
        user = self.check_user(msg_obj)
        if not object_id:
            raise InvalidParamsError
        self.check_owner(user, object_id)
        self.notes[object_id].update(**params)
        result = {'id': self.notes[object_id], 'message': 'Note has been updated', 'user': user}
        await queue.put((f"user_{user}", result))
        return result

    async def list(self, msg_obj: JSONObjectType, queue: asyncio.Queue, **params) -> List[Dict]:
        items = self.notes.values()
        if params['user']:                                              #3.8 assignment expression
            items = [item for item in items if item['user'] == params['user']]
        if params['name']:                                              #3.8 assignment expression
            items = [item for item in items if item['name'] == params['name']]
        return items

    async def subscribe_to_user(self, msg_obj: JSONObjectType, queue: asyncio.Queue, user: str = None):
        if not user:
            raise InvalidParamsError
        if user not in self.users:
            raise ObjectNotFoundError
        msg_obj.subscribe(f"user_{user}")

    async def unsubscribe_from_user(self, msg_obj: JSONObjectType, queue: asyncio.Queue, user: str = None):
        if not user:
            raise InvalidParamsError
        if user not in self.users:
            raise ObjectNotFoundError
        msg_obj.unsubscribe(f"user_{user}")
