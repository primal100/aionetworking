from .base import BaseServerAction, BaseClientAction


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
    exception_codes = {}

    async def do_one(self, msg):
        request_id = msg.get('id', None)
        func = getattr(self, msg['method'])
        params = msg.get('params', None)
        if isinstance(params, (tuple, list)):
            result = await func(*params)
        elif isinstance(params, dict):
            result = await func(**params)
        else:
            result = await func()
        if request_id:
            return {'jsonrpc': self.version, 'result': result, 'id': request_id}

    def response_on_exception(self, msg, exc): ...


class BaseJSONRPCClient(BaseClientAction):

        def __getattr__(self, item):
            if item in self.methods:
                return JSONRPCMethodClient(item)
            if item in self.notification_methods:
                return JSONRPCMethodNotification(item)
