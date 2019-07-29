from __future__ import annotations
import asyncio
from dataclasses import dataclass, field

from lib.formats.contrib.types import JSONObjectType

from typing import Dict


class AuthenticationError(BaseException):
    pass


class PermissionsError(BaseException):
    pass


@dataclass
class SampleJSONRPCServer:
    users: Dict[str, Dict] = field(default_factory=dict)
    notes: Dict[int, Dict] = field(default_factory=dict)
    last_id: int = 0

    exception_codes = {
        'AuthenticationError': {"code": -30000, "message": "Login failed"},
        'PermissionsError': {"code": -30001, "message": "You do not have permissions to perform this action"},
        'KeyError': {"code": -31000, "message": "That object does not exist"},
    }

    def add_user(self, user: str, password: str):
        self.users[user] = {'user': user, 'password': password}

    def delete_user(self, user: str):
        del self.users[user]

    def check_user(self, msg_obj: JSONObjectType):
        try:
            user = msg_obj.context['user']
            user_details = self.users[user]
            return user
        except KeyError:
            raise PermissionsError

    def check_owner(self, user: str, object_id: int) -> None:
        if not self.notes[object_id]['user'] == user:
            raise PermissionsError

    async def login(self, msg_obj: JSONObjectType, queue: asyncio.Queue, user: str, password: str):
        try:
            user_details = self.users[user]
        except KeyError:
            raise AuthenticationError
        if user_details['password'] == password:
            msg_obj.context['user'] = user
            return {'user': user, 'message': 'Login successful'}
        raise AuthenticationError

    async def logout(self, msg_obj: JSONObjectType, queue: asyncio.Queue):
        user = msg_obj.context['user']
        msg_obj.context['user'] = None
        return {'user': user, 'message': 'Logout successful'}

    async def create(self, msg_obj: JSONObjectType, queue: asyncio.Queue, name: str, text: str) -> Dict:
        user = self.check_user(msg_obj)
        self.last_id += 1
        note = {'id': self.last_id, 'name': name, 'text': text, 'user': user}
        self.notes[self.last_id] = note
        result = {'id': note['id'], 'message': 'New note has been created', 'user': user}
        await queue.put((f"user_{user}", result))
        return result

    async def delete(self, msg_obj: JSONObjectType, queue: asyncio.Queue, object_id: int) -> Dict:
        user = self.check_user(msg_obj)
        self.check_owner(user, object_id)
        del self.notes[object_id]
        result = {'id': object_id, 'message': 'Note has been deleted', 'user': user}
        await queue.put((f"user_{user}", result))
        return result

    async def get(self, msg_obj: JSONObjectType, queue: asyncio.Queue, object_id: int) -> Dict:
        return self.notes[object_id]

    async def update(self, msg_obj: JSONObjectType, queue: asyncio.Queue, id: int, **params) -> Dict:
        object_id = id
        user = self.check_user(msg_obj)
        self.check_owner(user, object_id)
        self.notes[object_id].update(**params)
        result = {'id': object_id, 'message': 'Note has been updated', 'user': user}
        await queue.put((f"user_{user}", result))
        return result

    async def subscribe_to_user(self, msg_obj: JSONObjectType, queue: asyncio.Queue, user: str):
        if user not in self.users:
            raise KeyError
        msg_obj.subscribe(f"user_{user}")

    async def unsubscribe_from_user(self, msg_obj: JSONObjectType, queue: asyncio.Queue, user: str):
        if user not in self.users:
            raise KeyError
        msg_obj.unsubscribe(f"user_{user}")
