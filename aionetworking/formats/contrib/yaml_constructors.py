import yaml
from .json import JSONObject
from .pickle import PickleObject
from typing import Type


def json_object_constructor(loader, node) -> Type[JSONObject]:
    return JSONObject


def load_json(Loader=yaml.SafeLoader):
    yaml.add_constructor('!JSON', json_object_constructor, Loader=Loader)


def pickle_object_constructor(loader, node) -> Type[PickleObject]:
    return PickleObject


def load_pickle(Loader=yaml.SafeLoader):
    yaml.add_constructor('!Pickle', pickle_object_constructor, Loader=Loader)