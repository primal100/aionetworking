import logging
import binascii
import asyncio
from lib import utils

logger = logging.getLogger('messageManager')


class BaseSender:

    @classmethod
    def from_config(cls, receiver_config, client_config, protocols, protocol_name):
        msg_protocol = protocols[protocol_name]
        return cls(msg_protocol)

    def __init__(self, protocol):
        self.msg_protocol = protocol

    @property
    def source(self):
        raise NotImplementedError

    async def send_msg(self, msg_encoded):
        raise NotImplementedError

    async def send_hex(self, hex_msg):
        await self.send_msg(binascii.unhexlify(hex_msg))

    async def __aenter__(self):
        raise NotImplementedError

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError

    async def send_msgs(self, msgs):
        for msg in msgs:
            await self.send_msg(msg)

    async def send_hex_msgs(self, hex_msgs):
        await self.send_msgs([binascii.unhexlify(hex_msg) for hex_msg in hex_msgs])

    async def encode_and_send_msgs(self, decoded_msgs):
        for decoded_msg in decoded_msgs:
            await self.encode_and_send_msg(decoded_msg)

    async def encode_and_send_msg(self, msg_decoded):
        msg = self.msg_protocol(self.source, decoded=msg_decoded)
        await self.send_msg(msg.encoded)

    async def play_recording(self, file_path, immediate=False):
        with open(file_path, 'rb') as f:
            content = f.read()
        packets = utils.unpack_recorded_packets(content)
        for seconds, sender, data in packets:
            if not immediate and seconds >= 1:
                await asyncio.sleep(seconds)
            await self.send_msg(data)


class BaseNetworkClient(BaseSender):
    sender_type = "Network client"
    peer_name = None
    sock_name = None
    src = None
    transport = None

    @classmethod
    def from_config(cls, receiver_config, client_config, protocols, protocol_name):
        msg_protocol = protocols[protocol_name]
        return cls(msg_protocol, receiver_config['host'], receiver_config['port'], receiver_config['ssl'],
                   client_config['src_ip'], client_config['src_port'])

    def __init__(self, protocol, host='127.0.0.1', port=4000, ssl=False, src_ip='', src_port=0):
        super(BaseNetworkClient, self).__init__(protocol)
        self.host = host
        self.port = port
        self.localaddr = (src_ip, src_port) if src_ip else None
        self.ssl = ssl
        self.dst = "%s:%s" % (host, port)

    @property
    def source(self):
        return self.sock_name[0]

    async def open_connection(self):
        raise NotImplementedError

    async def close_connection(self):
        raise NotImplementedError

    async def send_data(self, encoded_data):
        raise NotImplementedError

    async def __aenter__(self):
        logger.info("Opening %s connection to %s:%s" % (self.sender_type, self.host, self.port))
        await self.open_connection()
        self.peer_name = self.transport.get_extra_info('peername')
        self.sock_name = self.transport.get_extra_info('sockname')
        self.src = ':'.join(str(x) for x in self.sock_name)
        logger.info('%s Connected to %s from %s ' % (self.sender_type, self.dst, self.src))

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        logger.info("Closing %s connection to %s:%s" % (self.sender_type, self.host, self.port))
        await self.close_connection()

    async def send_msg(self, msg_encoded):
        logger.debug("Sending message to %s:%s" % (self.host, self.port))
        logger.debug(msg_encoded)
        await self.send_data(msg_encoded)
        logger.debug('Message sent')
