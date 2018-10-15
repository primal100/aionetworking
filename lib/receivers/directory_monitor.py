import os


class DirectoryMonitor:
    prev_message_time = 0

    def __init__(self, manager, config, loop=None):

        self.manager = manager
        self.config = config.receiver
        self.record = config.receiver.get('record', False)
        self.record_file = config.receiver.get('record_file', False)
        if self.record and not self.record_file:
            raise ConfigurationException('Please configure a record file when record is set to true')
        directories = self.config.get('directories')

        self.loop = loop or asyncio.get_event_loop()

        self.task = self.run(directories)

    def record_packet(self, msg, sender):
        if self.prev_message_time:
            message_timedelta = (datetime.datetime.now() - self.prev_message_time).seconds
        else:
            message_timedelta = 0
        self.prev_message_time = datetime.datetime.now()
        data = utils.pack_recorded_packet(message_timedelta, sender, msg)
        with open(self.record_file, 'a+') as f:
            f.write(data)

    async def handle_packet(self, user, data):
        logger.debug("Received msg from " + sender)
        logger.debug(data)
        await self.manager.manage(user, data)

    def close(self):
        logger.info('Cancelling Directory Monitor')
        self.task.cancel()
        logging.info('Directory Monitor Cancelled')

    async def monitor(self, directories):
        for d in directories:
            files = os.listdir(d)
            for file in files:
                with open(file, 'r') as f:
                    data = f.read()
                    self.loop.create_task(self.handle_packet(os.path.split(directory)[1], data))
                os.remove(file)
        await asyncio.sleep(1)
        await self.monitor(directories)

    def run(self, directories):
        logger.info('Starting Directory Monitor on %s' % directories)
        return loop.create_task(self.monitor(directories))
