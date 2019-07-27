from dataclasses import dataclass, field
from typing import Iterable, Dict, Any, Union

from lib.networking.protocols import NetworkConnectionProtocolType
from lib.wrappers.counters import Counters


@dataclass
class ConnectionsManager(Iterable):
    num = 0
    _connections: Dict[str, NetworkConnectionProtocolType] = field(init=False, default_factory=dict)
    _counters: Counters = field(init=False, default_factory=Counters)

    def add_connection(self, connection: NetworkConnectionProtocolType):
        self._connections[connection.peer_str] = connection
        self._counters.increment(connection.parent)

    def remove_connection(self, connection: Any):
        connection = self._connections.pop(connection.peer_str, None)
        self._counters.decrement(connection.parent)

    def num_connections(self, parent_id: int):
        return self._counters.get_num(parent_id)

    async def wait_all_connections_closed(self, parent_id: int, timeout: Union[int, float] = None):
        await self._counters.wait_zero(parent_id, timeout=timeout)

    def get(self, key: str, default: Any = None):
        return self._connections.get(key, default)

    def __iter__(self):
        for conn in self._connections.values():
            yield conn


connections_manager = ConnectionsManager()
