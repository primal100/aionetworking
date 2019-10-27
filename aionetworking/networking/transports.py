from asyncio import transports
from typing import Tuple, Any, Union, Optional


class DatagramTransportWrapper:
    def __init__(self, transport: transports.DatagramTransport, peer: Optional[Tuple[str, int]] = None):
        self._transport = transport
        self._peer = peer

    def __getattr__(self, name):
        return getattr(self._transport, name)

    def get_extra_info(self, name: Any, default: Any = ...) -> Any:
        if name == 'peername' and self._peer:
            return self._peer
        return self._transport.get_extra_info(name, default=default)

    def write(self, data: Any) -> None:
        if self._peer:
            self._transport.sendto(data, self._peer)
        else:
            self._transport.sendto(data)


TransportType = Union[transports.Transport, DatagramTransportWrapper]
