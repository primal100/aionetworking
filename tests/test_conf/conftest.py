import pytest

from lib.conf.mapping import MappingConfig


@pytest.fixture
def dict_parser():
    d = {

    }
    yield MappingConfig(d)


@pytest.fixture
def json_parser():
    pass


@pytest.fixture
def cp_parser():
    pass