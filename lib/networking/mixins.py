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

