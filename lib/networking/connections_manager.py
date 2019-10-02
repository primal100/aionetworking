from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from lib.conf.logging import connection_logger_cv
from typing import List, Dict, Any, DefaultDict


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

    def clear_server(self, parent_name: str):
        self._counters.remove(parent_name)

    def add_connection(self, connection: SimpleNetworkConnectionType) -> int:
        self._connections[connection.peer] = connection
        return self._counters.increment(connection.parent_name)

    def remove_connection(self, connection: Any) -> int:
        self._connections.pop(connection.peer)
        for key, subscribers in self._subscriptions.items():
            if connection in subscribers:
                subscribers.remove(connection)
        return self._counters.decrement(connection.parent_name)

    @property
    def total(self) -> int:
        return len(self._connections)

    def num_connections(self, parent_name: str) -> int:
        return self._counters.get_num(parent_name)

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
