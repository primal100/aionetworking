import logging

logger = logging.getLogger()


class BaseSender:

    @classmethod
    def from_config(cls, config):
        raise NotImplementedError

    @property
    def source(self):
        ###Todo
        return '127.0.0.1'

    async def send_msg(self, msg_encoded):
        raise NotImplementedError

    async def __aenter__(self):
        raise NotImplementedError

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError

    async def send_msgs(self, msgs):
        async with self:
            for msg in msgs:
                await self.send_msg(msg)

    async def encode_and_send_msgs(self, protocol, decoded_msgs):
        async with self:
            for decoded_msg in decoded_msgs:
                await self.encode_and_send_msg(protocol, decoded_msg)

    async def encode_and_send_msg(self, protocol, msg_decoded):
        msg = protocol(self.source, decoded=msg_decoded)
        await self.send_msg(msg.encoded)


class BaseNetworkClient(BaseSender):
    sender_type = "Network client"

    @classmethod
    def from_config(cls, config):
        return cls(config['host'], config['port'], config['ssl'])

    def __init__(self, host='127.0.0.1', port=4000, ssl=False):
        self.host = host
        self.port = port
        self.ssl = ssl
        self.dst = "%s:%s" % (host, port)

    async def open_connection(self):
        raise NotImplementedError

    async def close_connection(self):
        raise NotImplementedError

    async def send_data(self, encoded_data):
        raise NotImplementedError

    async def __aenter__(self):
        logger.info("Opening %s connection to %s:%s" % (self.sender_type, self.host, self.port))
        await self.open_connection()
        logger.info('%s Connected to %s:%s' % (self.sender_type, self.host, self.port))

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        logger.info("Closing %s connection to %s:%s" % (self.sender_type, self.host, self.port))
        await self.close_connection()
        logger.info('%s Connected to %s:%s closed' % (self.sender_type, self.host, self.port))

    async def send_msg(self, msg_encoded):
        logger.debug("Sending message to %s:%s" % (self.host, self.port))
        logger.debug(msg_encoded)
        await self.send_data(msg_encoded)
        logger.debug('Message sent')
