import asyncio
import pytest


class TestTCPServerOneWay:

    @pytest.mark.asyncio
    async def test_00_connection_call(self, connection_generator, connection, transport):
        new_connection = connection_generator()
        connection.parent_id = new_connection.parent_id
        assert new_connection == connection
        assert connection_generator.is_owner(new_connection)
        new_connection.connection_made(transport)
        task = asyncio.create_task(connection_generator.wait_closed())
        new_connection.connection_lost(None)
        await asyncio.wait_for(task, 1)