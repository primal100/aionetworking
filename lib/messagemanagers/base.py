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

    def __init__(self, app_name, message_cls, actions, config, loop=None):
        self.APP_NAME = app_name
        self.loop = loop or asyncio.get_event_loop()
        self.message_cls = message_cls
        self.config = config.message_manager_config
        self.msg_config = config.interface_config
        self.allowed_senders = self.config['allowed_senders']
        self.generate_timestamp = self.config['generate_timestamp']
        action_modules = [actions[a] for a in self.config['actions']]
        print_modules = [actions[a] for a in self.config['print_actions']]
        self.actions = [m.Action(app_name, config) for m in action_modules]
        self.print_actions = [m.Action(app_name, config, storage=False) for m in print_modules]
        self.aliases = self.config['aliases']

    def close(self):
        pass

    def get_alias(self, sender):
        return self.aliases.get(sender, sender)

    def check_sender(self, sender):
        if self.allowed_senders and sender not in self.allowed_senders:
            raise_message_from_not_authorized_host(sender, self.allowed_senders)
        return self.get_alias(sender)

    def make_message(self, sender, encoded, timestamp):
        return self.message_cls(sender, encoded, timestamp=timestamp, config=self.msg_config)

    async def manage_message(self, sender, encoded):
        host = self.check_sender(sender)
        if self.generate_timestamp:
            timestamp = datetime.datetime.now()
        else:
            timestamp = None
        if self.actions:
            await self.decode_run(host, encoded, timestamp)

    async def done(self):
        raise NotImplementedError

    def do_actions(self, msg):
        raise NotImplementedError

    async def decode_run(self, host, encoded, timestamp):
        raise NotImplementedError
