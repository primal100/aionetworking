from __future__ import annotations

from dataclasses import dataclass
from .protocols import RequesterProtocol

from typing import Any, Dict, Optional
from typing_extensions import Protocol


class MethodNotFoundError(BaseException):
    pass


class JSONRPCMethod:
    version = "2.0"

    def __init__(self, request_id: Optional[int], name: str):
        self.request_id = request_id
        self.name = name

    def __call__(self, *args, **kwargs) -> Dict[str, Any]:
        command = {"jsonrpc": self.version, "method": self.name}
        if self.request_id is not None:
            command['id'] = self.request_id
        if args:
            command['params'] = args
        elif kwargs:
            command['params'] = kwargs
        return command


class BaseJSONRPCClient(RequesterProtocol, Protocol):
    last_id = 0

    def __getattr__(self, item: str) -> JSONRPCMethod:
        if item in self.methods:
            self.last_id += 1
            return JSONRPCMethod(self.last_id, item)
        if item in self.notification_methods:
            return JSONRPCMethod(None, item)
        raise MethodNotFoundError(f'{item} not found in methods or notification methods for {self.__class__.__name__}')


@dataclass
class SampleJSONRPCClient(BaseJSONRPCClient):
    methods = ('login', 'authenticate', 'logout', 'create', 'update', 'delete', 'get', 'list')
    notification_methods = ('subscribe_to_user', 'unsubscribe_from_user')
