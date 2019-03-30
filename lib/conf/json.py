from collections import ChainMap
from pathlib import Path

from .mapping import MappingConfig

from typing import AnyStr


class JSONConfig(MappingConfig):

    def __init__(self, *jsons: AnyStr, **kwargs):
        mapping = ChainMap(*[self.get_json(json) for json in jsons])
        super().__init__(mapping, **kwargs)

    def get_json(self, json: AnyStr):
        formatted = json.format_map(self.defaults)
        return json.loads(formatted)


class JSONFileConfig(JSONConfig):

    def __init__(self, *file_names: Path, **kwargs):
        jsons = [path.read_text() for path in file_names]
        super().__init__(*jsons, **kwargs)


class JSONBFileConfig(JSONConfig):

    def __init__(self, *file_names: Path, **kwargs):
        jsons = [path.read_bytes() for path in file_names]
        super().__init__(*jsons, **kwargs)
