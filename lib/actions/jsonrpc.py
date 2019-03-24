from inspect import getfullargspec

from .base import BaseServerAction, BaseClientAction


class MethodNotFoundError(Exception):
    pass


class InvalidParamsError(Exception):
    pass


class BaseJSONRPCMethod:
    version = "2.0"

    def __init__(self, name):
        self.name = name

    def run(self, conn, command):
        conn.encode_and_send_msg(command)

    def base_command(self, *args, **kwargs):
        command = {"jsonrpc": self.version, "method": self.name}
        if args:
            command['params'] = args
        elif kwargs:
            command['params'] = kwargs
        return command


class JSONRPCMethodClient(BaseJSONRPCMethod):

    async def __call__(self, conn, *args, **kwargs):
        command = self.base_command(*args, **kwargs)
        command['id'] = conn.context.get('next_request_id', 0)
        conn.context['next_request_id'] = command['id'] + 1
        self.run(conn, command)
        #await response received


class JSONRPCMethodNotification(BaseJSONRPCMethod):
    def __call__(self, conn, *args, context=None, **kwargs):
        self.run(conn, self.base_command(*args, **kwargs))


class BaseJSONRPCServer(BaseServerAction):
    version = '2.0'
    exception_codes = {
        'InvalidRequestError': {"code": -32600, "message": "Invalid Request"},
        'MethodNotFoundError': {"code": -32601, "message": "Method not found"},
        'InvalidParamsError': {"code": -32602, "message": "Invalid params"},
        'InternalError': {"code": -32603, "message": "Invalid params"},
        'ParseError': {"code": -32700, "message": "Parse error"}
    }

    @staticmethod
    def check_args(exc):
        if "positional argument" or "keyword argument" in str(exc):
            raise InvalidParamsError

    async def do_one(self, msg):
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

    def response_on_decode_error(self, data, exc):
        return {"jsonrpc": self.version, "error": self.exception_codes.get('ParseError'), "id": None}

    def response_on_exception(self, msg_obj, exc):
        request_id = msg_obj.get('id', None)
        error = self.exception_codes.get(exc.__class__._name__, self.exception_codes['InvalidRequest'])
        return {"jsonrpc": self.version, "error": error, "id": request_id}


class SampleJSONRPCServer(BaseJSONRPCServer):

    async def test(self, param):
        return "Successfully processed {0}".format(param)


class BaseJSONRPCClient(BaseClientAction):
    methods = 'test',

    def __getattr__(self, item):
        if item in self.methods:
            return JSONRPCMethodClient(item)
        if item in self.notification_methods:
            return JSONRPCMethodNotification(item)
