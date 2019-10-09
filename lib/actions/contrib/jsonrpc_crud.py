from __future__ import annotations
import aio_pika
import asyncio
import aiosqlite
import secrets
from passlib.hash import pbkdf2_sha256

from lib.actions.jsonrpc import BaseJSONRPCApp
from lib.wrappers.schedulers import TaskScheduler

from typing import Dict


class AuthenticationError(BaseException):
    pass


class InvalidSessionError(BaseException):
    pass


class PermissionsError(BaseException):
    pass


class SampleJSONRPCSQLiteServer(BaseJSONRPCApp):
    _db = None
    _broker = None
    _channel = None

    exception_codes = {
        'AuthenticationError': {"code": -30000, "message": "Login failed"},
        'InvalidSessionError': {"code": -30001, "message": "Session is not valid. Login again."},
        'PermissionsError': {"code": -30001, "message": "You do not have permissions to perform this action"},
        'KeyError': {"code": -31000, "message": "That object does not exist"},
    }

    def __init__(self, db_driver=aiosqlite, dsn=":memory", supports_commit: bool = False, expire_sessions: int = 60,
                 broker_str: str= 'amqp://guest:guest@127.0.0.1/'):
        self._scheduler = TaskScheduler()
        self._expire_sessions_time = expire_sessions
        self._scheduler.call_coro_periodic(60, self._expire_sessions)
        self._ready = asyncio.Event()
        self._dsn = dsn
        self._db_driver = db_driver
        self._supports_commit = supports_commit
        self._broker_str = broker_str
        self._scheduler.create_task(self._connect_to_backends())

    @staticmethod
    def _create_tables_commands():
        return (
            "CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username VARCHAR(12) NOT NULL type UNIQUE,password VARCHAR(128) NOT NULL,summary TEXT)",
            "CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id CONSTRAINT fk_users FOREIGN KEY (user_id) REFERENCES users(id) NOT NULL,sessionkey VARCHAR(32) NOT NULL,timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)",
        )

    async def _expire_sessions(self):
        await self._run_write_sql("DELETE FROM sessions WHERE timestamp <= DATE('NOW','-%s MINUTE')", self._expire_sessions_time)

    async def _connect_to_db(self):
        self._db = await self._db_driver.connect(self._dsn)
        await self._create_tables()

    async def _connect_to_broker(self):
        if self._broker_str:
            self._broker = await aio_pika.connect_robust(self._broker_str)
            self._channel = await self._broker.channel()

    async def _connect_to_backends(self):
        await asyncio.wait([self._connect_to_db(), self._connect_to_broker()])
        self._ready.set()

    async def _run_sql(self, sql: str, *params):
        return await self._db.execute(sql, params)

    async def _run_select_one_sql(self, sql: str, *params):
        cursor = await self._run_sql(sql, *params)
        return await cursor.fetchone()

    async def _run_select_all_sql(self, sql: str, *params):
        cursor = await self._run_sql(sql, *params)
        return await cursor.fetchall()

    async def _run_write_sql(self, sql, *params):
        cursor = await self._run_sql(sql, *params)
        if self._supports_commit:
            await self._db.commit()
        return cursor

    async def _run_write_sql_fetchone(self, sql, *params):
        cursor = await self._run_write_sql(sql, params)
        return cursor.fetchone()

    async def _run_write_sql_fetchall(self, sql, *params):
        cursor = await self._run_write_sql(sql, params)
        return cursor.fetchall()

    async def _create_tables(self):
        sql_commands = self._create_tables_commands()
        await asyncio.wait((self._run_write_sql(sql) for sql in sql_commands))

    async def close(self):
        await self._scheduler.join()
        await self._db.close()

    async def hash_password(self, password: str):
        return await asyncio.get_event_loop().run_in_executor(None, pbkdf2_sha256.hash, password)

    async def verify_password(self, password: str, password_hash: str):
        verified = await asyncio.get_event_loop().run_in_executor(None, pbkdf2_sha256.verify, password, password_hash)
        if not verified:
            raise AuthenticationError

    async def _verify_session_id(self, session_key: str):
        "? Just update needed?"
        result = await self._run_select_one_sql("SELECT user_id FROM sessions WHERE sessionkey='%s' LIMIT 1", session_key)
        if result:
            await self._run_write_sql("UPDATE sessions SET timestamp=DATE('NOW') WHERE sessionkey='%s'", session_key)
            return result[0]
        raise InvalidSessionError

    async def login(self, username: str, password: str):
        user_details = await self._run_select_one_sql("SELECT password FROM users WHERE username='%s' LIMIT 1", username)
        if user_details:
            password_hash = user_details[0]
            await self.verify_password(password, password_hash)
            session_key = secrets.token_urlsafe(32)
            await self._run_write_sql("INSERT INTO sessions (user_id, sessionkey) VALUES (%s,%s)", username, session_key)
            return {'user': username, 'message': 'Login successful', 'sessionkey': session_key}
        raise AuthenticationError

    async def logout(self, session_key: str):
        result = await self._run_write_sql_fetchone("DELETE FROM sessions WHERE sessionkey='%s' LIMIT 1", session_key)
        if result:
            return {'message': 'Logout successful'}
        raise AuthenticationError

    async def add_user(self, username: str, password: str):
        hashed = await self.hash_password(password)
        return await self._run_write_sql_fetchone("INSERT INTO users (username, password) VALUES ('%s', '%s')", username,
                                                  hashed)

    async def _get_queue(self, name: str):
        return await self._channel.declare_queue(name, auto_delete=True)

    async def _send_update_notification(self, user_id: int):
        user_id, username, summary = await self.get_user(user_id)
        await self._channel.default_exchange.publish(
            aio_pika.Message(
                body=('User %s has updated their summary: %s' % (username, summary)).encode(),
        ),
            routing_key=username
        )

    async def update_user(self, session_key: str, summary: str):
        user_id = await self._verify_session_id(session_key)
        result = await self._run_write_sql_fetchone("UPDATE users SET summary='%s' WHERE user_id=%s", user_id, summary)
        if self._channel:
            task = self._scheduler.create_task(self._send_update_notification(user_id))
        return result

    async def delete_user(self, session_key: str):
        user_id = self._verify_session_id(session_key)
        await self._run_write_sql("DELETE FROM sessions WHERE user_id='%s'", user_id)
        return await self._run_write_sql("DELETE FROM users WHERE id = '%s'", user_id)

    async def get_user(self, user_id: int):
        return await self._run_select_one_sql("SELECT id,username,summary FROM users WHERE id=%s", user_id)

    async def get_user_by_username(self, username: str):
        return await self._run_select_one_sql("SELECT id,username,summary FROM users WHERE username='%s'", username)

    async def all_users(self):
        return await self._run_select_all_sql("SELECT * FROM users")

    async def subscribe_to_user(self, username: str):
        if not await self.get_user_by_username(username):
            raise KeyError
        if self._channel:
            queue = await self._get_queue(username)
            msg_obj.subscribe(f"user_{user}")

    async def unsubscribe_from_user(self, username: str):
        if not await self.get_user_by_username(username):
            raise KeyError
        msg_obj.unsubscribe(f"user_{user}")
