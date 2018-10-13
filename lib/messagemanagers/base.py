import asyncio
import logging
import datetime

logger = logging.getLogger()


class MessageFromNotAuthorizedHost(Exception):
    pass

def raise_message_from_not_authorized_host(sender, allowed_senders):
    msg = "Received message from unauthorized host %s. Authorized hosts are: %s" % (sender, allowed_senders)
    logger.error(msg)
    raise MessageFromNotAuthorizedHost(msg)


class BaseMessageManager:

    def __init__(self, message_cls, action_modules=(), print_modules=(),
                 interface_config, action_config, receiver_config, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.message_cls = message_cls
        self.allowed_senders = receiver_config['allowed_senders']
        self.generate_timestamp = receiver_config['generate_timestamp']
        self.interface_config = interface_config
        self.actions = [m.Action(action_config) for m in action_modules]
        self.print_actions = [m.Action(action_config) for m in print_modules]

    def check_sender(self, sender):
        if self.allowed_senders:
            try:
                host = self.allowed_senders[sender]
                return host
            except KeyError:
                raise_message_from_not_authorized_host(sender, self.allowed_senders)
        return sender

    async def manage(self, sender, encoded):
        host = self.check_sender(sender)
        if self.generate_timestamp:
            timestamp  = datetime.datetime.now()
        else
            timestamp = None
        if self.actions:
            await self.decode_run(host, encoded, timestamp)

    async def done(self):
        raise NotImplementedError

    def do_actions(self, msg):
        raise NotImplementedError

    async def decode_run(self, host, encoded, timestamp):
        raise NotImplementedError