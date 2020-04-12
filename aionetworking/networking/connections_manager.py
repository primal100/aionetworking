
from dataclasses import dataclass, field
from typing import Dict, Any


from aionetworking.types.networking import SimpleNetworkConnectionType
from aionetworking.futures.counters import Counters


endpoint_names = {}


def get_unique_name(name: str) -> str:
    index = endpoint_names.get(name)
    if index:
        full_name = f'{name}_{index}'
        endpoint_names[name] += 1
    else:
        full_name = name
        endpoint_names[name] = 2
    return full_name


def clear_unique_names() -> None:
    endpoint_names.clear()


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

    def remove_connection(self, connection: Any):
        self._connections.pop(connection.peer)

    def decrement(self, connection) -> int:
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

    def get(self, key: str, default: bool = "_raise") -> SimpleNetworkConnectionType:
        if default == "_raise":
            return self._connections[key]
        return self._connections.get(key, default)

    def __iter__(self) -> None:
        for conn in self._connections.values():
            yield conn


connections_manager = ConnectionsManager()
