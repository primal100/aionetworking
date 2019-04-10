from dataclasses import field

from .file_storage import BufferedFileStorage
from lib.utils import Record

from typing import TYPE_CHECKING, List
if TYPE_CHECKING:
    from dataclasses import dataclass
else:
    from pydantic.dataclasses import dataclass


@dataclass
class Recording(BufferedFileStorage):
    name = 'Recording'

    attr: str = 'record'
    senders: List[str] = field(default_factory=list)
    record: Record = field(default_factory=Record, init=False, repr=False, hash=False)

    def filter(self, msg):
        return self.senders and msg.context.get('alias', None) not in self.senders


