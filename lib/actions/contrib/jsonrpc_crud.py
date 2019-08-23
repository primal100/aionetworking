from __future__ import annotations
import asyncio
import aiosqlite

from lib.actions.jsonrpc import BaseJSONRPCApp
from lib.conf.context import context_cv
from lib.wrappers.schedulers import TaskScheduler

from typing import Dict


class AuthenticationError(BaseException):
    pass


class PermissionsError(BaseException):
    pass


class SampleJSONRPCSQLiteServer(BaseJSONRPCApp):

    exception_codes = {
        'AuthenticationError': {"code": -30000, "message": "Login failed"},
        'PermissionsError': {"code": -30001, "message": "You do not have permissions to perform this action"},
        'KeyError': {"code": -31000, "message": "That object does not exist"},
    }

    def __init__(self, dsn):
        self._scheduler = TaskScheduler()
        self._sql_queue = asyncio.Queue()
        self._task = None
        self._stop_event = asyncio.Event()
        self.dsn = ":memory:"

    @staticmethod
    def _create_tables_commands():
        return (
            "CREATE TABLE IF NOT EXISTS USER(id INTEGER PRIMARY KEY AUTOINCREMENT,username VARCHAR(12) NOT NULL,password(30) VARCHAR NOT NULL,summary TEXT)",
        )

    async def manage(self):
        async with aiosqlite.connect(self.dsn) as db:
            while not (self._stop_event.is_set() and self._sql_queue.empty()):
                sql, params, fut, commit = self._sql_queue.get()
                try:
                    cursor = await db.execute(sql, params)
                    if commit:
                        await db.commit()
                    result = cursor.fetchall()
                    fut.set_result(result)
                except Exception as e:
                    fut.set_exception(e)
                finally:
                    self._sql_queue.task_done()

    async def run_sql(self, sql, *params, commit=False):
        fut = asyncio.Future()
        await self._sql_queue.put((sql, params, fut, commit))
        return await fut

    async def run_write_sql(self, sql, *params):
        return await self.run_sql(sql, *params, commit=True)

    async def _create_tables(self):
        sql_commands = self._create_tables_commands()
        await asyncio.wait((self.run_write_sql(sql) for sql in sql_commands))

    async def close(self):
        self._stop_event.set()
        await self._sql_queue.join()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            await super().close()

    async def start_for_server(self):
        self._task = self._scheduler.create_task(self.manage())
        await self._create_tables()

    async def add_user(self, user_id: str, password: str):
        return await self.run_write_sql("INSERT INTO USERS (USERNAME, PASSWORD) VALUES ('%s', '%s')", user_id, password)

    async def update_user(self, user_id: int, summary: str):
        return await self.run_write_sql("UPDATE USERS SET SUMMARY = '%s' WHERE USER_ID = '%s'", user_id, summary)

    async def delete_user(self, user_id: str):
        return await self.run_write_sql("DELETE FROM USERS WHERE USERNAME = ('%s')", user_id)

    async def get_user(self, user_id: str):
        return await self.run_sql("SELECT * FROM USERS WHERE ID = ('%s')", user_id)

    async def all_users(self):
        return await self.run_sql("SELECT * FROM USERS")

    def _check_user(self):
        context = context_cv.get()
        user_id = context['user']
        self.get_user(user_id)
        return user_id

    async def login(self, user: str, password: str):
        user_details = await self.get_user(user)
        if user_details['password'] == password:
            context = context_cv.get()
            context['user'] = user
            return {'user': user, 'message': 'Login successful'}
        raise AuthenticationError

    async def logout(self):
        context = context_cv.get()
        user = context['user']
        context['user'] = None
        return {'user': user, 'message': 'Logout successful'}

    async def create(self, user_id: int) -> Dict:
        user = self._check_user(user_id)
        await self.delete_user(user_id)
        result = {'id': user_id, 'message': 'User has been deleted'}
        await self.notifications_queue.put((f"user_{user}", result))
        return result

    async def delete(self, user_id: int) -> Dict:
        user = self._check_user(user_id)
        await self.delete_user(user_id)
        result = {'id': user_id, 'message': 'User has been deleted'}
        await self.notifications_queue.put((f"user_{user}", result))
        return result

    async def get(self) -> Dict:
        return self.all_users()

    async def update(self, user_id: int, summary: str) -> Dict:
        object_id = id
        user = self._check_user(msg_obj)
        self.check_owner(user, object_id)
        self.update_user(user_id, summary)
        result = {'id': object_id, 'message': 'User has been updated'}
        await self.notifications_queue.put((f"user_{user}", result))
        return result

    async def subscribe_to_user(self, user: str):
        if user not in self.users:
            raise KeyError
        msg_obj.subscribe(f"user_{user}")

    async def unsubscribe_from_user(self, user: str):
        if user not in self.users:
            raise KeyError
        msg_obj.unsubscribe(f"user_{user}")
