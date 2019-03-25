from .file_storage import BufferedFileStorage
from lib.utils import Record


class Recording(BufferedFileStorage):
    name = 'Recording'
    key = 'Recording'
    first_msg_time = 0

    #Dataclass_fields
    attr: str = 'record'
    senders: tuple = ()

    def __post_init__(self):
        self.record = Record()

    def filter(self, msg):
        return self.senders and msg.context.get('alias', None) not in self.senders


