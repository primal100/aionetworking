import logging
import settings
from pathlib import Path

from lib import utils
from lib.utils import underline

from typing import TYPE_CHECKING, Sequence, Mapping, AnyStr
if TYPE_CHECKING:
    from lib.protocols.base import BaseProtocol
else:
    BaseProtocol = None

logger = logging.getLogger(settings.LOGGER_NAME)


class BaseAction:

    action_name = ''
    default_data_dir = ""
    store_write_mode = 'w+'
    store_many_write_mode = 'a'
    single_extension = "txt"
    multi_extension = "txt"
    configurable = {'base_path': Path}

    @classmethod
    def from_config(cls, storage: bool=True, **kwargs):
        config = settings.CONFIG.section_as_dict(cls.action_name, **cls.configurable)
        config['base_path'] = settings.CONFIG.path_for_action(cls.action_name, cls.default_data_dir)
        logger.debug('Found configuration for %s:%s', cls.action_name, config)
        config.update(kwargs)
        return cls(storage=storage, **config)

    def __init__(self, base_path: Path=None, storage: bool=True):

        if storage:
            logger.info("Setting up action %s for storage", self.action_name)
            self.base_path = base_path or settings.DATA_DIR.joinpath(self.default_data_dir)
            logger.info("Using directory %s for %s", self.base_path, self.action_name)
            self.base_path.mkdir(parents=True, exist_ok=True)
        else:
            logger.info("Setting up action %s for print", self.action_name)

    def get_content(self, msg: BaseProtocol):
        raise NotImplementedError

    def get_content_multi(self, msg: BaseProtocol):
        return self.get_content(msg)

    def print_msg(self, msg: BaseProtocol):
        return self.get_content(msg)

    def print(self, msg: BaseProtocol):
        if not msg.filter_by_action(self, True):
            print(underline("Message received from %s:" % msg.sender))
            print(self.print_msg(msg))
            print("")
        else:
            logger.debug("Message filtered for action %s print", self.action_name)

    def do(self, msg: BaseProtocol):
        if not msg.filter_by_action(self, False):
            path = self.base_path.joinpath(msg.storage_path_single)
            path.mkdir(exist_ok=True, parents=True)
            file_path = msg.unique_filename(path, self.get_file_extension(msg))
            logger.debug('Storing %s message in %s', self.action_name, file_path)
            with file_path.open(self.store_write_mode) as f:
                f.write(self.get_content(msg))
        else:
            logger.debug("Message filtered for action %s", self.action_name)

    def get_file_extension(self, msg: BaseProtocol) -> str:
        return self.single_extension

    def get_multi_file_extension(self, msg: BaseProtocol) -> str:
        return self.multi_extension

    def writes_for_store_many(self, msgs: Sequence[BaseProtocol]) -> Mapping[Path, AnyStr]:
        writes = {}
        for msg in msgs:
            if not msg.filter_by_action(self, False):
                file_name = msg.storage_filename_multiple.with_suffix("." + self.get_multi_file_extension(msg))
                if file_name in writes:
                    writes[file_name] += self.get_content_multi(msg)
                else:
                    writes[file_name] = self.get_content_multi(msg)
        return writes

    def store_many(self, msgs: Sequence[BaseProtocol]):
        logger.debug('Storing %s messages for action %s', len(msgs), self.action_name)
        writes = self.writes_for_store_many(msgs)
        logger.debug('Storing in files %s',  list(writes.keys()))
        utils.write_to_files(self.base_path, self.store_many_write_mode, writes)

    def do_multiple(self, msgs):
        self.store_many(msgs)

