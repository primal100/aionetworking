import asyncio
import pytest


class TestTCPServerOneWay:

    @pytest.mark.asyncio
    async def test_00_connection_call(self, protocol_factory, connection, transport):
        new_connection = protocol_factory()
        connection.parent_id = new_connection.parent_id
        assert new_connection == connection
        assert protocol_factory.is_owner(new_connection)
        new_connection.connection_made(transport)
        task = asyncio.create_task(protocol_factory.wait_all_closed())
        new_connection.connection_lost(None)
        await asyncio.wait_for(task, 1)