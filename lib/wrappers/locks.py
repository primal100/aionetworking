from asyncio import Event


class ExceptionEvent:
    _exception = None

    def set_exception(self, exc: BaseException):
        self._exception = exc
        for fut in self._waiters:
            if not fut.done():
                fut.set_exception(self._exception)