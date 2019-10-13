from asyncio import transports
from typing import Tuple, Any, Union


class DatagramTransportWrapper:
    def __init__(self, transport: transports.DatagramTransport, peer: Tuple[str, int] = None):
        self._transport = transport
        self._peer = peer
        self._is_closing = False

    def __getattr__(self, name):
        return getattr(self._transport, name)

    def get_extra_info(self, name: Any, default: Any = ...) -> Any:
        if name == 'peername' and self._peer:
            return self._peer
        return self._transport.get_extra_info(name, default=default)

    def write(self, data: Any) -> None:
        self._transport.sendto(data, self._peer)


TransportType = Union[transports.Transport, DatagramTransportWrapper]
