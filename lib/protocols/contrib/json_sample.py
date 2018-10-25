from lib.utils import cached_property
from .json import BaseJSONProtocol
from datetime import datetime
from typing import Sequence, Mapping


class JsonSampleProtocol(BaseJSONProtocol):
    protocol_name = "JsonLogHandler"

    @cached_property
    def uid(self):
        return self.decoded['id']

    @cached_property
    def file_extension(self) -> str:
        return 'json'

    @staticmethod
    def readable_time(action:Mapping) -> str:
        return datetime.fromtimestamp(action['timestamp']).strftime("%Y-%m-%d %H:%m:%S.%f")

    @cached_property
    def prettified(self) -> Sequence[Mapping]:
        return [
                    {
                        'time': self.readable_time(action),
                        'object_id': action['object_id'],
                        'operation': action['operation'].capitalize()
                    } for action in self.decoded['actions']
            ]

    def summaries(self) -> Sequence[Sequence]:
        return [
            (
                action['time'],
                action['object_id'],
                action['operation']
            ) for action in self.prettified
        ]
