from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any


from lib.networking.types import SimpleNetworkConnectionType
from lib.wrappers.counters import Counters


@dataclass
class ConnectionsManager:
    _connections: Dict[str, SimpleNetworkConnectionType] = field(init=False, default_factory=dict)
    _counters: Counters = field(init=False, default_factory=Counters)

    def clear(self):
        self._connections.clear()
        self._counters.clear()

    def clear_server(self, parent_name: str):
        self._counters.remove(parent_name)

    def add_connection(self, connection: SimpleNetworkConnectionType) -> int:
        self._connections[connection.peer] = connection
        return self._counters.increment(connection.parent_name)

    def remove_connection(self, connection: Any) -> int:
        self._connections.pop(connection.peer)
        return self._counters.decrement(connection.parent_name)

    @property
    def total(self) -> int:
        return len(self._connections)

    def num_connections(self, parent_name: str) -> int:
        return self._counters.get_num(parent_name)

    async def wait_num_connections(self, parent_name: str, num: int) -> None:
        await self._counters.wait_for(parent_name, num)

    async def wait_num_has_connected(self, parent_name: str, num: int) -> None:
        await self._counters.wait_for_total_increments(parent_name, num)

    async def wait_all_messages_processed(self, parent_name: str) -> None:
        tasks = [conn.close_actions() for conn in self if conn.parent_name == parent_name]
        await asyncio.wait(tasks)

    def get(self, key: str) -> SimpleNetworkConnectionType:
        return self._connections[key]

    def __iter__(self) -> None:
        for conn in self._connections.values():
            yield conn


connections_manager = ConnectionsManager()
