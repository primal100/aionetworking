from lib.utils import cached_property
from .json import BaseJSONInterface
from datetime import datetime


class JsonSampleInterface(BaseJSONInterface):
    interface_name = "JsonLogHandler"

    @cached_property
    def uid(self):
        return self.decoded['id']

    @cached_property
    def file_extension(self):
        return 'json'

    @staticmethod
    def readable_time(action):
        return datetime.fromtimestamp(action['timestamp']).strftime("%Y-%m-%d %H:%m:%S.%f")

    @cached_property
    def prettified(self):
        return [
                    {
                        'time': self.readable_time(action),
                        'object_id': action['object_id'],
                        'operation': action['operation'].capitalize()
                    } for action in self.decoded['actions']
            ]

    @cached_property
    def summaries(self):
        return [
            (
                action['time'],
                action['object_id'],
                action['operation']
            ) for action in self.prettified
        ]
