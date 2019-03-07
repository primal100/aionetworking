class TCP:
    ssl_section_name:str = None
    ssl_class = None
    configurable = {
        'sslhandshaketimeout': int
    }

    @classmethod
    def from_config(cls, *args, logger=None, config=None, cp=None, **kwargs):
        ssl = cls.ssl_cls.get_context('SSLServer', logger=logger, cp=cp)
        return super().from_config(*args, cp=cp, config=config, ssl=ssl, **kwargs)

    def __init__(self, *args, ssl: bool = None, sslhandshaketimeout: int=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssl = ssl
        self.ssl_handshake_timeout = sslhandshaketimeout


class ClientProtocolMixin:
    logger_name = 'sender'

    @property
    def client(self) -> str:
        return self.sock

    @property
    def server(self) -> str:
        return self.peer


class ServerProtocolMixin:
    logger_name = 'receiver'

    @property
    def client(self) -> str:
        if self.alias:
            return '%s(%s)' % (self.alias, self.peer)
        return self.peer

    @property
    def server(self) -> str:
        return self.sock
