import asyncio
from collections import OrderedDict


class DictQueue(OrderedDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = asyncio.Lock()
        self.check_empty()

    def check_empty(self):
        if not self and not self.lock.locked():
            self.lock.acquire()

    def check_not_empty(self):
        if self and self.lock.locked():
            self.lock.release()
        self.check_empty()

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if self.lock.locked():
            self.lock.release()

    def __delattr__(self, name):
        super().__delattr__(name)
        self.check_not_empty()

    def __clear__(self):
        super().clear()
        self.check_empty()

    def __delitem__(self, key):
        super().__delitem__(key)
        self.check_not_empty()

    ####uses del
    def pop(self, k):
        item = super().pop(k)
        self.check_not_empty()
        return item

    def popitem(self, last: bool = ...):
        item = super().popitem(last=last)
        self.check_not_empty()
        return item

    async def _get(self, last):
        await self.lock.acquire()
        return self.popitem(last=last)

    async def get_next(self):
        return await self._get(last=False)

    async def get_last(self):
        return await self._get(last=True)

    def pop_all(self):
        items = self.items()
        self.clear()
        return items

    def _pop_all_sorted(self, index):
        items = self.pop_all()
        return sorted(items, key=lambda x: x[index])

    def pop_all_sorted_by_key(self):
        return self._pop_all_sorted(0)

    def pop_all_sorted_by_value(self):
        return self._pop_all_sorted(1)
