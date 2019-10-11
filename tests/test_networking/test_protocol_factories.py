import asyncio
import pytest
import pickle


class TestStreamProtocolFactories:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, protocol_factory, connection, transport, connection_is_stored):
        new_connection = protocol_factory()
        assert protocol_factory.logger == new_connection.logger
        assert new_connection == connection
        assert protocol_factory.is_owner(new_connection)
        new_connection.connection_made(transport)
        if connection_is_stored:
            await asyncio.wait_for(protocol_factory.wait_num_connected(1), timeout=1)
        await asyncio.wait_for(new_connection.wait_connected(), timeout=1)
        new_connection.connection_lost(None)
        await asyncio.wait_for(protocol_factory.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)

    @pytest.mark.asyncio
    async def test_01_pickle_protocol_factory(self, protocol_factory):
        data = pickle.dumps(protocol_factory)
        factory = pickle.loads(data)
        assert factory == protocol_factory
        await protocol_factory.close()
