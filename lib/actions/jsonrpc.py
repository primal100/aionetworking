from .base import BaseReceiverAction, BaseSenderAction
from typing import TYPE_CHECKING, MutableMapping, AnyStr, NoReturn

if TYPE_CHECKING:
    from lib.formats.base import BaseMessageObject
else:
    BaseMessageObject = None


class MethodNotFoundError(Exception):
    pass


class InvalidParamsError(Exception):
    pass


class JSONRPCMethod:
    version = "2.0"

    def __init__(self, name: str):
        self.name = name

    def base_command(self, *args, **kwargs) -> MutableMapping:
        command = {"jsonrpc": self.version, "method": self.name}
        if args:
            command['params'] = args
        elif kwargs:
            command['params'] = kwargs
        return command


class BaseJSONRPCServer(BaseReceiverAction):
    version = '2.0'
    exception_codes = {
        'InvalidRequestError': {"code": -32600, "message": "Invalid Request"},
        'MethodNotFoundError': {"code": -32601, "message": "Method not found"},
        'InvalidParamsError': {"code": -32602, "message": "Invalid params"},
        'InternalError': {"code": -32603, "message": "Invalid params"},
        'ParseError': {"code": -32700, "message": "Parse error"}
    }

    @staticmethod
    def check_args(exc: Exception) -> NoReturn:
        if "positional argument" or "keyword argument" in str(exc):
            raise InvalidParamsError

    async def do_one(self, msg: BaseMessageObject) -> MutableMapping:
        request_id = msg.get('id', None)
        try:
            func = getattr(self, msg['method'])
        except KeyError:
            raise MethodNotFoundError
        params = msg.get('params', None)
        try:
            if isinstance(params, (tuple, list)):
                result = await func(*params)
            elif isinstance(params, dict):
                result = await func(**params)
            else:
                result = await func()
        except TypeError as exc:
            self.check_args(exc)
            raise exc
        if request_id:
            return {'jsonrpc': self.version, 'result': result, 'id': request_id}

    def response_on_decode_error(self, data: AnyStr, exc: Exception) -> MutableMapping:
        return {"jsonrpc": self.version, "error": self.exception_codes.get('ParseError'), "id": None}

    def response_on_exception(self, msg_obj: BaseMessageObject, exc: Exception) -> MutableMapping:
        request_id = msg_obj.get('id', None)
        error = self.exception_codes.get(exc.__class__.__name__, self.exception_codes['InvalidRequest'])
        return {"jsonrpc": self.version, "error": error, "id": request_id}


class SampleJSONRPCServer(BaseJSONRPCServer):

    async def test(self, param):
        return f"Successfully processed {param}"


class BaseJSONRPCClient(BaseSenderAction):
    methods = 'test',

    def __getattr__(self, item) -> JSONRPCMethod:
        if item in self.methods:
            return JSONRPCMethod(item)
        if item in self.notification_methods:
            return JSONRPCMethod(item)
