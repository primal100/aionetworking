import logging
import datetime

logger = logging.getLogger('messageManager')


class MessageFromNotAuthorizedHost(Exception):
    pass


def raise_message_from_not_authorized_host(sender, allowed_senders):
    msg = "Received message from unauthorized host %s. Authorized hosts are: %s" % (sender, allowed_senders)
    logger.error(msg)
    raise MessageFromNotAuthorizedHost(msg)


class BaseMessageManager:
    batch = False

    def __init__(self, app_name, protocol, actions, config):
        self.app_name = app_name
        self.protocol = protocol
        self.config = config.message_manager_config
        self.protocol_config = config.protocol_config
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
        alias = self.aliases.get(sender, sender)
        if alias != sender:
            logger.debug('Alias found for %s: %s' % (sender, alias))
        return alias

    def check_sender(self, sender):
        if self.allowed_senders and sender not in self.allowed_senders:
            raise_message_from_not_authorized_host(sender, self.allowed_senders)
        if self.allowed_senders:
            logger.debug('Sender is in allowed senders.')
        return self.get_alias(sender)

    def make_message(self, sender, encoded, timestamp):
        return self.protocol(sender, encoded, timestamp=timestamp, config=self.protocol_config)

    async def manage_message(self, sender, encoded):
        logger.debug('Managing message from ' + sender)
        host = self.check_sender(sender)
        if self.generate_timestamp:
            timestamp = datetime.datetime.now()
            logger.debug('Generated timestamp %s' % timestamp)
        else:
            timestamp = None
        if self.actions:
            await self.decode_run(host, encoded, timestamp)

    def do_actions(self, msg):
        raise NotImplementedError

    async def decode_run(self, host, encoded, timestamp):
        raise NotImplementedError
