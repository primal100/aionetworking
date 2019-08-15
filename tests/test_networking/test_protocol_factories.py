import asyncio
import pytest
import pickle


class TestTCPServerOneWay:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, protocol_factory, connection, transport, connection_is_stored,
                                           connections_manager):
        new_connection = protocol_factory()
        assert new_connection.logger == new_connection.logger
        assert new_connection == connection
        assert protocol_factory.is_owner(new_connection)
        new_connection.connection_made(transport)
        task = asyncio.create_task(protocol_factory.close())
        await asyncio.sleep(0)
        if connection_is_stored:
            assert not task.done()
        new_connection.connection_lost(None)
        await asyncio.wait_for(task, 1)

    @pytest.mark.asyncio
    async def test_01_wait_num_connected(self, protocol_factory, transport, connection_is_stored, connections_manager):
        new_connection = protocol_factory()
        if connection_is_stored:
            task = asyncio.create_task(protocol_factory.wait_num_has_connected(1))
            await asyncio.sleep(0)
            assert not task.done()
            new_connection.connection_made(transport)
            await asyncio.wait_for(task, timeout=1)
            new_connection.connection_lost(None)
            await asyncio.wait_for(protocol_factory.wait_num_has_connected(1), timeout=1)
        else:
            new_connection.connection_made(transport)
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(protocol_factory.wait_num_has_connected(1), timeout=1)
            await asyncio.wait_for(protocol_factory.wait_num_has_connected(0), timeout=1)

    @pytest.mark.asyncio
    async def test_02_pickle_protocol_factory(self, protocol_factory):
        data = pickle.dumps(protocol_factory)
        factory = pickle.loads(data)
        assert factory == protocol_factory
        await protocol_factory.close()
