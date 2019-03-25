from tempfile import TemporaryDirectory

from dataclasses import Field
from typing import NoReturn, MutableMapping, Iterable


class ConfigurationException(Exception):
    pass


class BaseConfig:

    def __init__(self, logger_name: str = 'root'):
        self.logger_name = logger_name
        from lib import settings
        tmp_dir = TemporaryDirectory(prefix=settings.APP_NAME)
        self.defaults = {
            'Testdir': settings.TESTS_DIR,
            'Tmpdir': tmp_dir,
            'Develdir': settings.ROOT_DIR,
            'Userhome': settings.USER_HOME,
            "~": settings.USER_HOME,
            'Osdatadir': settings.OSDATA_DIR,
        }
        self.defaults.update({
            'appname': settings.APP_NAME.replace(' ', '').lower(),
        })

    @property
    def receiver(self):
        raise NotImplementedError

    @property
    def sender_type(self):
        raise NotImplementedError

    @property
    def protocol(self):
        raise NotImplementedError

    def configure_logging(self) -> NoReturn:
        raise NotImplementedError

    def section_as_dict(self, section: str, fields=Iterable[Field]) -> MutableMapping:
        raise NotImplementedError
