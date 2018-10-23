import asyncio
import binascii
import logging

from lib import utils
logger = logging.getLogger('messageManager')


class BaseEndpointMixin:

    @classmethod
    def from_config(cls):
        import definitions
        msg_protocol = protocols[protocol_name]
        return cls(msg_protocol, **kwargs)

    def __init__(self, protocol, **kwargs):
        self.msg_protocol = protocol

    @property
    def source(self):
        raise NotImplementedError

    @property
    def dst(self):
        raise NotImplementedError

    async def __aenter__(self):
        raise NotImplementedError

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError

    async def send_data(self, msg_encoded):
        raise NotImplementedError

    async def send_msg(self, msg_encoded):
        logger.debug("Sending message to %s" % self.dst)
        logger.debug(msg_encoded)
        await self.send_data(msg_encoded)
        logger.debug('Message sent')

    async def send_hex(self, hex_msg):
        await self.send_msg(binascii.unhexlify(hex_msg))

    async def send_msgs(self, msgs):
        for msg in msgs:
            await self.send_msg(msg)
            await asyncio.sleep(0.001)

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
        if immediate:
            await self.send_msgs([p[2] for p in packets])
        for seconds, sender, data in packets:
            if not immediate and seconds >= 1:
                await asyncio.sleep(seconds)
            await self.send_msg(data)

