class MessageFromNotAuthorizedHost(BaseException):
    pass


class MethodNotFoundError(BaseException):
    pass


class ConnectionAlreadyClosedError(BaseException):
    pass


class ProtocolException(BaseException):
    pass


class RemoteConnectionClosedError(BaseException):
    pass