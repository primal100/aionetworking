import logging
import datetime
import asyncio

logger = logging.getLogger('messageManager')


class MessageFromNotAuthorizedHost(Exception):
    pass


def raise_message_from_not_authorized_host(sender, allowed_senders):
    msg = "Received message from unauthorized host %s. Authorized hosts are: %s" % (sender, allowed_senders)
    logger.error(msg)
    raise MessageFromNotAuthorizedHost(msg)


class BaseMessageManager:
    batch = False

    @classmethod
    def from_config(cls, protocol):
        import definitions
        kwargs = definitions.CONFIG.message_manager_config
        store_modules = [definitions.ACTIONS[a] for a in kwargs.pop['actions']]
        print_modules = [definitions.ACTIONS[a] for a in kwargs.pop['print_actions']]
        store_actions = [m.Action.from_config(storage=True) for m in store_modules]
        print_actions = [m.Action.from_config(storage=False) for m in print_modules]
        return cls(protocol, store_actions, print_actions, **kwargs)

    def __init__(self, protocol, store_actions, print_actions, allowed_senders=(), generate_timestamp=False,
                 aliases=None, interval=1):
        self.protocol = protocol
        self.allowed_senders = allowed_senders
        self.aliases = aliases or None
        self.generate_timestamp = generate_timestamp
        self.interval = interval
        self.store_actions = store_actions
        self.print_actions = print_actions
        self.queue = asyncio.Queue()
        self.process_queue_task = asyncio.get_event_loop().create_task(self.process_queue_later())

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
        return self.protocol(sender, encoded, timestamp=timestamp)

    async def manage_message(self, sender, encoded):
        logger.debug('Managing message from ' + sender)
        host = self.check_sender(sender)
        if self.generate_timestamp:
            timestamp = datetime.datetime.now()
            logger.debug('Generated timestamp %s' % timestamp)
        else:
            timestamp = None
        logger.debug('Adding message from %s to asyncio queue' % host)
        await self.queue.put((host, encoded, timestamp))

    async def process_queue_later(self):
        await asyncio.sleep(self.interval)
        try:
            await self.process_queue()
        finally:
            await self.process_queue_later()

    async def process_queue(self):
        logger.debug('Processing asyncio queue')
        msgs = []
        try:
            while not self.queue.empty():
                item = self.queue.get_nowait()
                logger.debug('Took item from queue')
                sender, encoded, timestamp = item
                msg = self.make_message(sender, encoded, timestamp)
                if not msg.filter():
                    msgs.append(msg)
                else:
                    logger.debug("Message was filtered out")
            self.do_actions(msgs)
        finally:
            for msg in msgs:
                logger.debug("Setting task done on queue")
                self.queue.task_done()

    async def close(self):
        logger.info('Closing Batch Message Manager')
        try:
            timeout = self.interval + 1
            logger.info('Waiting %s seconds for queue to empty' % timeout)
            await asyncio.wait_for(self.queue.join(), timeout=timeout + 1)
            logger.info('Queue empty. Cancelling task')
        except asyncio.TimeoutError:
            logger.error('Queue did not empty. Cancelling task with messages in queue.')
        self.process_queue_task.cancel()
        logger.info('Batch Message Manager closed')

    def do_actions(self, msg):
        raise NotImplementedError
