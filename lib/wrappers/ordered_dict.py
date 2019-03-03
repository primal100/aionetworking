import asyncio
from collections import OrderedDict


class DictQueue(OrderedDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = asyncio.Event()
        self.check_not_empty()

    def check_empty(self):
        if not self.has_items():
            self.event.clear()

    def check_not_empty(self):
        if self.has_items():
            self.event.set()

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.check_not_empty()

    def __delattr__(self, name):
        super().__delattr__(name)
        self.check_empty()

    def __delitem__(self, key):
        super().__delitem__(key)
        self.check_empty()

    def has_items(self):
        return bool(self)

    async def _get(self, last):
        while not self.has_items():
            await self.event.wait()
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
