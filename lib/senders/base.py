from abc import ABC, abstractmethod
import asyncio

from pydantic.dataclasses import dataclass

from lib.conf.types import Logger
from lib.networking.mixins import ClientProtocolMixin
from lib.networking.asyncio_protocols import BaseNetworkProtocol

from typing import NoReturn


@dataclass
class BaseSender(ABC):
    name = 'sender'
    logger: Logger = 'sender'

    @property
    def loop(self) -> asyncio.SelectorEventLoop:
        return asyncio.get_event_loop()

    async def __aenter__(self) -> ClientProtocolMixin:
        return await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> NoReturn:
        await self.stop()

    async def start(self) -> ClientProtocolMixin:
        pass

    async def stop(self):
        pass


@dataclass
class BaseNetworkClient(ABC, BaseSender):
    name = "Network client"
    conn = None
    transport = None

    host: str = '127.0.0.1'
    port: int = 4000
    srcip: str = None
    srcport: int = 0
    protocol:  BaseNetworkProtocol = None

    @abstractmethod
    async def open_connection(self) -> ClientProtocolMixin: ...

    async def close_connection(self): ...

    async def start(self) -> ClientProtocolMixin:
        self.logger.info("Opening %s connection to %s", self.sender_type, self.dst)
        connection = await self.open_connection()
        self.logger.info("Connection open")
        return connection

    async def stop(self) -> NoReturn:
        self.logger.info("Closing %s connection to %s", self.sender_type, self.dst)
        await self.close_connection()
        self.logger.info("Connection closed")
