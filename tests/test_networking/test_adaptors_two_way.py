import pytest
import asyncio
import logging

from aionetworking.networking.exceptions import MethodNotFoundError


@pytest.mark.connections('all_twoway_server')
class TestTwoWayReceiverAdaptor:
    @pytest.mark.asyncio
    async def test_00_on_data_received(self, tmp_path, adaptor, echo_encoded, echo_response_encoded, timestamp,
                                       assert_recordings_ok, queue, json_codec):
        task = adaptor.on_data_received(echo_encoded, timestamp)
        assert adaptor.codec == json_codec
        msg = await queue.get()
        await adaptor.close()
        assert task.done()
        assert msg == echo_response_encoded
        await assert_recordings_ok

    @pytest.mark.asyncio
    async def test_01_notifications(self, tmp_path, adaptor, echo_notification_client_encoded, timestamp,
                                    echo_notification_server_encoded, queue):
        task = adaptor.on_data_received(echo_notification_client_encoded, timestamp)
        msg = await queue.get()
        await adaptor.close()
        assert task.done()
        assert msg == echo_notification_server_encoded

    @pytest.mark.asyncio
    async def test_02_on_exception(self, adaptor, echo_exception_request_encoded, caplog, queue, critical_logging_only,
                                   echo_exception_response_encoded, timestamp):
        task = adaptor.on_data_received(echo_exception_request_encoded, timestamp)
        msg = await queue.get()
        await adaptor.close()
        assert task.done()
        assert msg == echo_exception_response_encoded
        caplog.clear()

    @pytest.mark.asyncio
    async def test_03_response_on_decode_error(self, adaptor, echo_request_invalid_json, timestamp,
                                               echo_decode_error_response_encoded, queue, critical_logging_only):
        task = adaptor.on_data_received(echo_request_invalid_json, timestamp)
        msg = await queue.get()
        await adaptor.close()
        assert task.done()
        assert msg == echo_decode_error_response_encoded


@pytest.mark.connections('all_twoway_client')
class TestSenderAdaptorTwoWay:
    @pytest.mark.asyncio
    async def test_00_wait_notification(self, adaptor, echo_notification_object):
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(adaptor.wait_notification(), timeout=1)
        adaptor._notification_queue.put_nowait(echo_notification_object)
        notification = await adaptor.wait_notification()
        assert notification == echo_notification_object

    def test_01_get_notification(self, adaptor, echo_notification_object):
        adaptor._notification_queue.put_nowait(echo_notification_object)
        notification = adaptor.get_notification()
        assert notification == echo_notification_object

    def test_02_all_notifications(self, adaptor, echo_notification_object):
        adaptor._notification_queue.put_nowait(echo_notification_object)
        adaptor._notification_queue.put_nowait(echo_notification_object)
        objs = list(adaptor.all_notifications())
        assert objs == [echo_notification_object, echo_notification_object]

    @pytest.mark.asyncio
    async def test_03_on_data_received_response(self, adaptor, echo_response_encoded, timestamp,
                                                echo_response_object, json_codec):
        a = logging
        fut = asyncio.Future()
        adaptor._scheduler._futures[1] = fut
        task = adaptor.on_data_received(echo_response_encoded, timestamp)
        result = await asyncio.wait_for(fut, timeout=200)
        await task
        assert result == echo_response_object
        assert adaptor.codec == json_codec

    @pytest.mark.asyncio
    async def test_04_on_data_received_notification(self, adaptor, echo_notification_server_encoded,
                                                    echo_notification_object, timestamp):
        task = adaptor.on_data_received(echo_notification_server_encoded, timestamp)
        result = await asyncio.wait_for(adaptor.wait_notification(), timeout=2)
        await task
        assert result == echo_notification_object

    async def assert_response(self, queue, echo_encoded, adaptor, echo_response_encoded, timestamp, task1,
                              echo_response_object):
        msg = await queue.get()
        assert msg == echo_encoded
        task2 = adaptor.on_data_received(echo_response_encoded, timestamp=timestamp)
        result = await asyncio.wait_for(task1, timeout=2)
        await task2
        assert result == echo_response_object

    @pytest.mark.asyncio
    async def test_05_send_data_and_wait(self, adaptor, echo_encoded, echo_response_encoded, timestamp,
                                         echo_response_object, queue):
        task1 = asyncio.create_task(adaptor.send_data_and_wait(1, echo_encoded))
        await self.assert_response(queue, echo_encoded, adaptor, echo_response_encoded, timestamp, task1,
                                   echo_response_object)

    @pytest.mark.asyncio
    async def test_06_send_msg_and_wait(self, adaptor, echo_request_object, echo_encoded,
                                        echo_response_encoded, timestamp, echo_response_object, queue):
        task1 = asyncio.create_task(adaptor.send_msg_and_wait(echo_request_object))
        await self.assert_response(queue, echo_encoded, adaptor, echo_response_encoded, timestamp, task1,
                                   echo_response_object)

    @pytest.mark.asyncio
    async def test_07_encode_send_wait(self, adaptor, echo, echo_encoded, timestamp,
                                       echo_response_encoded, echo_response_object, queue):
        task1 = asyncio.create_task(adaptor.encode_send_wait(echo))
        await self.assert_response(queue, echo_encoded, adaptor, echo_response_encoded, timestamp, task1,
                                   echo_response_object)

    @pytest.mark.asyncio
    async def test_08_run_method_and_wait(self, adaptor, echo_encoded, timestamp,
                                          echo_response_encoded, echo_response_object, queue):
        task1 = asyncio.create_task(adaptor.echo())
        await self.assert_response(queue, echo_encoded, adaptor, echo_response_encoded, timestamp, task1,
                                   echo_response_object)

    @pytest.mark.asyncio
    async def test_09_run_method_notification(self, adaptor, echo_notification_client_encoded, queue,
                                              echo_notification_server_encoded, echo_notification_object, timestamp):
        adaptor.subscribe()
        msg = await queue.get()
        assert msg == echo_notification_client_encoded
        task2 = adaptor.on_data_received(echo_notification_server_encoded, timestamp=timestamp)
        result = await asyncio.wait_for(adaptor.wait_notification(), timeout=2)
        await task2
        assert result == echo_notification_object

    @pytest.mark.asyncio
    async def test_10_no_method(self, adaptor):
        with pytest.raises(MethodNotFoundError):
            adaptor.ech()
