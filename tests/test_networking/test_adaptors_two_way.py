import pytest
import asyncio

from pathlib import Path

from lib.formats.recording import get_recording_from_file
from lib.networking.exceptions import MethodNotFoundError
from lib.utils import alist


class TestTwoWayReceiverAdaptor:
    def test_00_post_init(self, two_way_receiver_adaptor, json_codec):
        assert two_way_receiver_adaptor.codec == json_codec

    @pytest.mark.asyncio
    async def test_01_on_data_received(self, tmp_path, two_way_receiver_adaptor, echo_encoded, timestamp,
                                       echo_response_encoded, echo_recording_data, queue):
        task = two_way_receiver_adaptor.on_data_received(echo_encoded, timestamp)
        msg = await queue.get()
        await two_way_receiver_adaptor.close()
        assert task.done()
        assert msg == echo_response_encoded
        expected_file = Path(tmp_path / 'Recordings/127.0.0.1.recording')
        assert expected_file.exists()
        packets = await alist(get_recording_from_file(expected_file))
        assert packets == echo_recording_data

    @pytest.mark.asyncio
    async def test_02_notifications(self, tmp_path, two_way_receiver_adaptor, echo_notification_client_encoded, timestamp,
                                    echo_notification_server_encoded, queue):
        task = two_way_receiver_adaptor.on_data_received(echo_notification_client_encoded, timestamp)
        msg = await queue.get()
        await two_way_receiver_adaptor.close()
        assert task.done()
        assert msg == echo_notification_server_encoded

    @pytest.mark.asyncio
    async def test_03_on_exception(self, two_way_receiver_adaptor, echo_exception_request_encoded,
                                   echo_exception_response_encoded, timestamp, queue, critical_logging_only):
        task = two_way_receiver_adaptor.on_data_received(echo_exception_request_encoded, timestamp)
        msg = await queue.get()
        await two_way_receiver_adaptor.close()
        assert task.done()
        assert msg == echo_exception_response_encoded

    @pytest.mark.asyncio
    async def test_04_response_on_decode_error(self, two_way_receiver_adaptor, echo_request_invalid_json, timestamp,
                                               echo_decode_error_response_encoded, queue, critical_logging_only):
        task = two_way_receiver_adaptor.on_data_received(echo_request_invalid_json, timestamp)
        msg = await queue.get()
        await two_way_receiver_adaptor.close()
        assert task.done()
        assert msg == echo_decode_error_response_encoded


class TestSenderAdaptorTwoWay:
    def test_00_post_init(self, two_way_sender_adaptor, json_client_codec):
        assert two_way_sender_adaptor.codec == json_client_codec

    @pytest.mark.asyncio
    async def test_01_wait_notification(self, two_way_sender_adaptor, echo_notification_object):
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(two_way_sender_adaptor.wait_notification(), timeout=1)
        two_way_sender_adaptor._notification_queue.put_nowait(echo_notification_object)
        notification = await two_way_sender_adaptor.wait_notification()
        assert notification == echo_notification_object

    def test_02_get_notification(self, two_way_sender_adaptor, echo_notification_object):
        two_way_sender_adaptor._notification_queue.put_nowait(echo_notification_object)
        notification = two_way_sender_adaptor.get_notification()
        assert notification == echo_notification_object

    def test_03_all_notifications(self, two_way_sender_adaptor, echo_notification_object):
        two_way_sender_adaptor._notification_queue.put_nowait(echo_notification_object)
        two_way_sender_adaptor._notification_queue.put_nowait(echo_notification_object)
        objs = list(two_way_sender_adaptor.all_notifications())
        assert objs == [echo_notification_object, echo_notification_object]

    @pytest.mark.asyncio
    async def test_04_on_data_received_response(self, two_way_sender_adaptor, echo_response_encoded, timestamp,
                                                echo_response_object):
        fut = asyncio.Future()
        two_way_sender_adaptor._scheduler._futures[1] = fut
        task = two_way_sender_adaptor.on_data_received(echo_response_encoded, timestamp)
        result = await asyncio.wait_for(fut, timeout=1)
        await task
        assert result == echo_response_object

    @pytest.mark.asyncio
    async def test_05_on_data_received_notification(self, two_way_sender_adaptor, echo_notification_server_encoded,
                                                    echo_notification_object, timestamp):
        task = two_way_sender_adaptor.on_data_received(echo_notification_server_encoded, timestamp)
        result = await asyncio.wait_for(two_way_sender_adaptor.wait_notification(), timeout=1)
        await task
        assert result == echo_notification_object

    async def assert_response(self, queue, echo_encoded, two_way_sender_adaptor, echo_response_encoded, timestamp, task1,
                           echo_response_object):
        msg = await queue.get()
        assert msg == echo_encoded
        task2 = two_way_sender_adaptor.on_data_received(echo_response_encoded, timestamp=timestamp)
        result = await asyncio.wait_for(task1, timeout=1)
        await task2
        assert result == echo_response_object

    @pytest.mark.asyncio
    async def test_06_send_data_and_wait(self, two_way_sender_adaptor, echo_encoded, echo_response_encoded, timestamp,
                                         echo_response_object, queue):
        task1 = asyncio.create_task(two_way_sender_adaptor.send_data_and_wait(1, echo_encoded))
        await self.assert_response(queue, echo_encoded, two_way_sender_adaptor, echo_response_encoded, timestamp, task1,
                                   echo_response_object)

    @pytest.mark.asyncio
    async def test_07_send_msg_and_wait(self, two_way_sender_adaptor, echo_request_object, echo_encoded,
                                        echo_response_encoded, timestamp, echo_response_object, queue):
        task1 = asyncio.create_task(two_way_sender_adaptor.send_msg_and_wait(echo_request_object))
        await self.assert_response(queue, echo_encoded, two_way_sender_adaptor, echo_response_encoded, timestamp, task1,
                                   echo_response_object)

    @pytest.mark.asyncio
    async def test_08_encode_send_wait(self, two_way_sender_adaptor, echo, echo_encoded, timestamp,
                                       echo_response_encoded, echo_response_object, queue):
        task1 = asyncio.create_task(two_way_sender_adaptor.encode_send_wait(echo))
        await self.assert_response(queue, echo_encoded, two_way_sender_adaptor, echo_response_encoded, timestamp, task1,
                                   echo_response_object)

    @pytest.mark.asyncio
    async def test_09_run_method_and_wait(self, two_way_sender_adaptor, echo_encoded, timestamp,
                                          echo_response_encoded, echo_response_object, queue):
        task1 = asyncio.create_task(two_way_sender_adaptor.echo())
        await self.assert_response(queue, echo_encoded, two_way_sender_adaptor, echo_response_encoded, timestamp, task1,
                                   echo_response_object)

    @pytest.mark.asyncio
    async def test_10_run_method_notification(self, two_way_sender_adaptor, echo_notification_client_encoded, queue,
                                              echo_notification_server_encoded, echo_notification_object, timestamp):
        two_way_sender_adaptor.subscribe()
        msg = await queue.get()
        assert msg == echo_notification_client_encoded
        task2 = two_way_sender_adaptor.on_data_received(echo_notification_server_encoded, timestamp=timestamp)
        result = await asyncio.wait_for(two_way_sender_adaptor.wait_notification(), timeout=1)
        await task2
        assert result == echo_notification_object

    @pytest.mark.asyncio
    async def test_11_no_method(self, two_way_sender_adaptor):
        with pytest.raises(MethodNotFoundError):
            two_way_sender_adaptor.ech()
