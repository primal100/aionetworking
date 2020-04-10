import pytest   # noinspection PyPackageRequirements
import asyncio

from aionetworking.compatibility import (supports_task_name, get_task_name, get_current_task_name, set_task_name,
                                         set_current_task_name)


class TestTaskNames:
    @pytest.mark.asyncio
    async def test_00_get_task_name(self, task):
        if supports_task_name():
            assert task.get_name() == get_task_name(task) == "Task-99"
        else:
            assert str(id(task)) == get_task_name(task)

    @pytest.mark.asyncio
    async def test_01_get_current_task_name(self):
        current_task = asyncio.current_task()
        task_name = get_current_task_name()
        if supports_task_name():
            assert current_task.get_name() == task_name
        else:
            assert str(id(current_task)) == task_name

    @staticmethod
    def _prepare_current_task(name) -> asyncio.Task:
        current_task = asyncio.current_task()
        if supports_task_name():
            current_task.set_name(name)
            assert current_task.get_name() == name
        return current_task

    @pytest.mark.asyncio
    async def test_02_set_current_task_name(self):
        current_task = self._prepare_current_task('Task-10')
        set_current_task_name('TestTask')
        current_task_name = get_current_task_name()
        if supports_task_name():
            assert current_task.get_name() == current_task_name == 'Task-10_TestTask'
        else:
            assert str(id(current_task)) == current_task_name

    @pytest.mark.asyncio
    async def test_03_set_task_name_without_hierarchy(self, task):
        set_task_name(task, "HelloWorld", include_hierarchy=False)
        if supports_task_name():
            assert task.get_name() == get_task_name(task) == "Task-99_HelloWorld"
        else:
            assert str(id(task)) == get_task_name(task)

    @pytest.mark.asyncio
    async def test_04_set_task_name_include_hierarchy(self, task):
        # Following line required to change task name, pycharm gives error if task is not retrieved
        _ = self._prepare_current_task('Task-10')
        set_task_name(task, "HelloWorld")
        if supports_task_name():
            assert task.get_name() == get_task_name(task) == "Task-10:Task-99_HelloWorld"
        else:
            assert str(id(task)) == get_task_name(task)
        await task
