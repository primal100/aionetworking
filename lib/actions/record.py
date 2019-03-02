import asyncio

from .file_storage import BufferedFileStorage
from lib.utils import Record

class Recording(BufferedFileStorage):
    name = 'Recording'
    key = 'Recording'
    first_msg_time = 0
    configurable = BufferedFileStorage.configurable.copy()
    configurable.update({'senders': tuple})

    def __init__(self, *args, senders=(), **kwargs):
        super(Recording, self).__init__(*args, **kwargs)
        self.senders = senders
        self.record = Record()

    def get_data(self, msg):
        return self.record.pack_client_msg(msg)

    def filter(self, msg):
        return self.senders and msg.sender not in self.senders

    def get_logs_extra(self, msg):
        return {'sender': msg.sender}
