import pytest
import asyncio


class TestNetworkConnections:

    @pytest.mark.asyncio
    async def test_00_multiple_connections(self, connections_manager, simple_network_connection):
        parent_id = simple_network_connection.parent
        peer_str = simple_network_connection.peer_str
        connections_manager.add_connection(simple_network_connection)
        assert connections_manager.num_connections(parent_id) == 1
        connection = connections_manager.get(peer_str)
        assert connection == simple_network_connection
        with pytest.raises(asyncio.TimeoutError):
            await connections_manager.wait_all_connections_closed(parent_id, timeout=0.2)
        connections_manager.remove_connection(simple_network_connection)
        assert connections_manager.num_connections(parent_id) == 0
        await connections_manager.wait_all_connections_closed(parent_id)

    @pytest.mark.asyncio
    async def test_01_multiple_connections_iter(self, connections_manager, simple_network_connections):
        connections_manager.add_connection(simple_network_connections[0])
        connections_manager.add_connection(simple_network_connections[1])
        connections = list(connections_manager)
        assert connections == simple_network_connections

    def test_02_subscribe_notify_unsubscribe(self, connections_manager, simple_network_connection, deque):
        connections_manager.add_connection(simple_network_connection)
        connections_manager.notify("test", "message sent")
        with pytest.raises(IndexError):
            deque.pop()
        connections_manager.subscribe(simple_network_connection.peer_str, "test")
        assert connections_manager.is_subscribed(simple_network_connection, "test") is True
        assert connections_manager.peer_is_subscribed(simple_network_connection.peer_str, "test") is True
        connections_manager.notify("test", "message sent")
        assert deque.pop() == "message sent"
        with pytest.raises(IndexError):
            deque.pop()
        connections_manager.unsubscribe(simple_network_connection.peer_str, "test")
        assert connections_manager.is_subscribed(simple_network_connection, "test") is False
        assert connections_manager.peer_is_subscribed(simple_network_connection.peer_str, "test") is False
        connections_manager.notify("test", "message sent")
        with pytest.raises(IndexError):
            deque.pop()
