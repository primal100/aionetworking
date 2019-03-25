import asyncio

from lib.conf.types import BaseSwappable
from lib import definitions

from typing import TYPE_CHECKING, Sequence, Generator, Any, AnyStr, NoReturn, Type
if TYPE_CHECKING:
    from lib.formats.base import BaseMessageObject
    from lib.conf.types import BaseConfigurable
else:
    BaseMessageObject = None
    BaseConfigurable = None


class BaseReceiverAction(BaseSwappable):
    name = 'receiver action'
    key = 'ReceiverAction'
    default_logger_name = 'receiver'

    #Dataclass fields
    timeout: int = 5

    @classmethod
    def get_swappable(cls, name: str) -> Type[BaseConfigurable]:
        return definitions.ACTIONS[name]

    def __post_init__(self):
        self.logger = self.logger.get_child("actions")
        self._outstanding_tasks = []

    async def do_one(self, msg: BaseMessageObject) -> Any:
        raise NotImplementedError

    def do_many(self, msgs: Sequence[BaseMessageObject]) -> Generator[Sequence[BaseMessageObject, asyncio.Task], None, None]:
        return self.do_many_parallel(msgs)

    def do_many_parallel(self, msgs: Sequence[BaseMessageObject]) -> Generator[Sequence[BaseMessageObject, asyncio.Task], None, None]:
        for msg in msgs:
            if not self.filter(msg):
                task = asyncio.create_task(self.do_one(msg))
                self._outstanding_tasks += task
                yield msg, task

    def do_many_sequential(self, msgs: Sequence[BaseMessageObject]) -> Generator[Sequence[BaseMessageObject, Any], None, None]:
        for msg in msgs:
            if not self.filter(msg):
                yield msg, self.do_one(msg)

    def filter(self, msg: BaseMessageObject) -> bool:
        return msg.filter()

    async def wait_complete(self) -> NoReturn:
        if self._outstanding_tasks:
            self.logger.debug('Waiting for tasks to complete')
            try:
                await asyncio.wait(self._outstanding_tasks, timeout=self.timeout)
            finally:
                self._outstanding_tasks.clear()

    async def close(self) -> NoReturn:
        await self.wait_complete()

    def response_on_decode_error(self, data: AnyStr, exc: Exception) -> Any:
        pass

    def response_on_exception(self, msg: BaseMessageObject, exc: Exception) -> Any:
        pass


class BaseSenderAction(BaseSwappable):
    name = 'sender'
    key = 'SenderAction'
    default_logger_name = 'sender'
    methods = ()
    notification_methods = ()

    #Dataclass fields
    timeout: int = 5

    @classmethod
    def get_swappable(cls, name: str) -> Type[BaseConfigurable]:
        return definitions.ACTIONS[name]

    def __post_init__(self):
        self.logger = self.logger.get_child("actions")

