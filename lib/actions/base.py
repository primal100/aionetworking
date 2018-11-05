import asyncio
import logging
from pathlib import Path

import settings
from lib.utils import underline

from typing import TYPE_CHECKING, Sequence, Mapping, AnyStr
if TYPE_CHECKING:
    from lib.protocols.base import BaseProtocol
else:
    BaseProtocol = None

logger = logging.getLogger(settings.LOGGER_NAME)


class BaseRawAction:

    action_name = ''
    default_data_dir = ""
    store_write_mode = 'w+'
    store_many_write_mode = 'a'
    single_extension = "txt"
    multi_extension = "txt"
    configurable = {'base_path': Path}
    requires_decoding: bool = True

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

    def print(self, msg: BaseProtocol, sender: str):
        if not self.filtered(msg, True):
            print(underline("Message received from %s:" % sender))
            print(self.print_msg(msg))
            print("")
        else:
            logger.debug("Message filtered for action %s print", self.action_name)

    async def write_to_file(self, file_path: Path, data: AnyStr, write_mode: str):
        logger.debug('Storing %s message in %s', self.action_name, file_path)
        async with settings.FILE_OPENER.open(file_path, write_mode) as f:
            await f.write(data)
        logger.debug('%s message stored in %s', self.action_name.capitalize(), file_path)

    def unique_filename(self, base_path: Path, msg) -> Path:
        extension = self.get_file_extension(msg)
        base_file_path = base_path.joinpath(self.get_storage_filename_single(msg))
        file_path = base_file_path.with_suffix("." + extension)
        i = 1
        while True:
            try:
                file_path.touch(exist_ok=False)
                break
            except FileExistsError:
                file_path = Path(base_file_path.parent, "%s_%s%s" % (base_file_path.stem, i, file_path.suffix))
                i += 1
        return file_path

    def do(self, msg: BaseProtocol, sender: str):
        if not self.filtered(msg):
            file_path = self.get_storage_path_single(msg)
            file_path.touch()
            task = asyncio.create_task(self.write_to_file(file_path, self.get_content(msg), self.store_write_mode))
            return task
        else:
            logger.debug("Message filtered for action %s", self.action_name)
            return None

    def get_storage_path_single(self, msg):
        return Path('')

    def get_storage_filename_single(self, msg):
        return Path('')

    def get_file_extension(self, msg: BaseProtocol) -> str:
        return self.single_extension

    def get_multi_file_extension(self, msg: BaseProtocol) -> str:
        return self.multi_extension

    def get_storage_filename_multiple(self, msg):
        return Path('')

    def filtered(self, msg, storage=True):
        return False

    def writes_for_store_many(self, msgs: Sequence[BaseProtocol]) -> Mapping[Path, AnyStr]:
        writes = {}
        for msg in msgs:
            if not self.filtered(msg):
                file_name = self.get_storage_filename_multiple(msg)
                if file_name in writes:
                    writes[file_name] += self.get_content_multi(msg)
                else:
                    writes[file_name] = self.get_content_multi(msg)
        return writes

    def write_to_files(self, base_path: Path, write_mode: str, file_writes: Mapping[Path, AnyStr]):
        """
        Takes a dictionary containing filepaths (keys) and data to write to each one (values)
        """
        for file_name in file_writes.keys():
            file_path = base_path.joinpath(file_name)
            asyncio.create_task(self.write_to_file(file_path, file_writes[file_name], write_mode))

    def store_many(self, msgs: Sequence[BaseProtocol]):
        writes = self.writes_for_store_many(msgs)
        self.write_to_files(self.base_path, self.store_many_write_mode, writes)

    def do_multiple(self, msgs):
        self.store_many(msgs)


class BaseAction(BaseRawAction):

    def get_content(self, msg: BaseProtocol):
        raise NotImplementedError

    def get_storage_filename_multiple(self, msg):
        return msg.storage_filename_multi.with_suffix("." + self.get_multi_file_extension(msg))

    def filtered(self, msg, print=False):
        return msg.filter_by_action(self, print)

    def get_storage_path_single(self, msg):
        path = self.base_path.joinpath(msg.storage_path_single, msg.storage_filename_single)
        path.parent.mkdir(exist_ok=True, parents=True)
        return self.unique_filename(path, msg)

