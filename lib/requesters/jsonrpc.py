from __future__ import annotations
from abc import ABC

from .base import BaseRequester

from typing import Any, Dict


class MethodNotFoundError(BaseException):
    pass


class JSONRPCMethod:
    version = "2.0"

    def __init__(self, name: str):
        self.name = name

    def __call__(self, *args, **kwargs) -> Dict[str, Any]:
        command = {"jsonrpc": self.version, "method": self.name}
        if args:
            command['params'] = args
        elif kwargs:
            command['params'] = kwargs
        return command


class BaseJSONRPCClient(BaseRequester, ABC):

    def __getattr__(self, item: str) -> JSONRPCMethod:
        if item in self.methods:
            return JSONRPCMethod(item)
        if item in self.notification_methods:
            return JSONRPCMethod(item)
        raise MethodNotFoundError(f'{item} not found in methods or notification methods for {self.__class__.__name__}')


class SampleJSONRPCClient(BaseJSONRPCClient):
    methods = ('login', 'authenticate', 'logout', 'create', 'update', 'delete', 'get', 'list')
    notification_methods = ('subscribe_to_user', 'unsubscribe_from_user')
