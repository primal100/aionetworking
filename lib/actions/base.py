from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass, field
import warnings

from lib.conf.logging import Logger
from lib.formats.base import BaseMessageObject

from typing import Sequence, List, Tuple, Generator, Any, AnyStr, NoReturn


warnings.filterwarnings("ignore", message="fields may not start with an underscore")


@dataclass
class BaseAction(ABC):
    name = 'receiver action'
    logger: Logger = Logger('receiver')

    timeout: int = 5
    _outstanding_tasks: List = field(default_factory=list, init=False, repr=False, hash=False)

    @classmethod
    def swap_cls(cls, name: str):
        from lib.definitions import ACTIONS
        return ACTIONS[name]

    def __post_init__(self):
        self.logger = self.logger.get_child(name='actions')

    def _do_many_parallel(self, msgs: Sequence[BaseMessageObject]) -> Generator[Tuple[BaseMessageObject, asyncio.Task], None, None]:
        for msg in msgs:
            if not self.filter(msg):
                task = asyncio.create_task(self.do_one(msg))
                self._outstanding_tasks.append(task)
                yield msg, task

    def _do_many_sequential(self, msgs: Sequence[BaseMessageObject]) -> Generator[Tuple[BaseMessageObject, Any], None, None]:
        for msg in msgs:
            if not self.filter(msg):
                yield msg, self.do_one(msg)

    async def _wait_complete(self) -> NoReturn:
        if self._outstanding_tasks:
            self.logger.debug('Waiting for tasks to complete')
            try:
                await asyncio.wait(self._outstanding_tasks, timeout=self.timeout)
            finally:
                self._outstanding_tasks.clear()

    def filter(self, msg: BaseMessageObject) -> bool:
        return msg.filter()

    async def close(self) -> NoReturn:
        await self._wait_complete()

    def response_on_decode_error(self, data: AnyStr, exc: Exception) -> Any:
        pass

    def response_on_exception(self, msg: BaseMessageObject, exc: Exception) -> Any:
        pass

    @abstractmethod
    async def do_one(self, msg: BaseMessageObject) -> Any: ...

    def do_many(self, msgs: Sequence[BaseMessageObject]) -> Sequence[Tuple[BaseMessageObject, asyncio.Task]]:
        return list(self._do_many_parallel(msgs))

