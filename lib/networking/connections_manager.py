from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Union, DefaultDict

from lib.networking.types import SimpleNetworkConnectionType
from lib.wrappers.counters import Counters
from lib.factories import list_defaultdict


@dataclass
class ConnectionsManager:
    _connections: Dict[str, SimpleNetworkConnectionType] = field(init=False, default_factory=dict)
    _counters: Counters = field(init=False, default_factory=Counters)
    _subscriptions: DefaultDict[Any, List[SimpleNetworkConnectionType]] = field(init=False,
                                                                                default_factory=list_defaultdict)

    def clear(self):
        self._connections.clear()
        self._counters.clear()
        self._subscriptions.clear()

    def add_connection(self, connection: SimpleNetworkConnectionType) -> None:
        self._connections[connection.peer] = connection
        self._counters.increment(connection.parent_id)

    def remove_connection(self, connection: Any):
        connection = self._connections.pop(connection.peer, None)
        for key, subscribers in self._subscriptions.items():
            if connection in subscribers:
                subscribers.remove(connection)
        self._counters.decrement(connection.parent_id)

    @property
    def total(self) -> int:
        return len(self._connections)

    def num_connections(self, parent_id: int) -> int:
        return self._counters.get_num(parent_id)

    def subscribe(self, peer_str: str, subscribe_key: Any) -> None:
        connection = self.get(peer_str)
        if not self.is_subscribed(connection, subscribe_key):
            self._subscriptions[subscribe_key].append(connection)

    def unsubscribe(self, peer_str: str, subscribe_key: Any) -> None:
        connection = self.get(peer_str)
        try:
            self._subscriptions[subscribe_key].remove(connection)
        except ValueError:
            pass

    def is_subscribed(self, connection: SimpleNetworkConnectionType, subscribe_key: str):
        return connection in self._subscriptions.get(subscribe_key, [])

    def peer_is_subscribed(self, peer_str: str,  subscribe_key: str):
        connection = self.get(peer_str)
        return self.is_subscribed(connection, subscribe_key)

    def send_msg_to(self, peer_str: str, decoded: Any) -> None:
        connection = self.get(peer_str)
        connection.encode_and_send_msg(decoded)

    def notify(self, subscribe_key: Any, decoded: Any) -> None:
        for connection in self._subscriptions[subscribe_key]:
            connection.encode_and_send_msg(decoded)

    async def wait_num_connections(self, parent_id: int, num: int) -> None:
        await self._counters.wait_for(parent_id, num)

    async def wait_num_has_connected(self, parent_id: int, num: int) -> None:
        await self._counters.wait_for_total_increments(parent_id, num)

    async def wait_all_messages_processed(self, parent_id: int) -> None:
        tasks = [conn.close_actions() for conn in self if conn.parent_id == parent_id]
        await asyncio.wait(tasks)

    async def wait_all_connections_closed(self, parent_id: int) -> None:
        await self.wait_num_connections(parent_id, 0)

    def get(self, key: str) -> SimpleNetworkConnectionType:
        return self._connections.get(key)

    def __iter__(self) -> None:
        for conn in self._connections.values():
            yield conn


connections_manager = ConnectionsManager()