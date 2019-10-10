import pytest
import asyncio
from datetime import timedelta
from pathlib import Path
import json
from json.decoder import JSONDecodeError

from lib.networking.exceptions import MethodNotFoundError
from lib.utils import Record, time_coro


class TestTwoWayReceiverAdaptor:
    def test_00_post_init(self, two_way_receiver_adaptor, json_codec):
        assert two_way_receiver_adaptor.codec == json_codec

    @pytest.mark.asyncio
    async def test_01_on_data_received(self, tmp_path, two_way_receiver_adaptor, json_rpc_login_request_encoded,
                                       json_rpc_logout_request_encoded, json_rpc_login_response,
                                       json_rpc_logout_response, timestamp, json_recording, json_recording_data, deque):
        two_way_receiver_adaptor.on_data_received(json_rpc_login_request_encoded, timestamp)
        two_way_receiver_adaptor.on_data_received(json_rpc_logout_request_encoded, timestamp + timedelta(seconds=1))
        await two_way_receiver_adaptor.close_actions(None, timeout=0.5)
        msg1 = deque.pop()
        msg2 = deque.pop()
        msgs = [json.loads(msg1), json.loads(msg2)]
        assert sorted(msgs, key=lambda x: x['id']) == sorted([json_rpc_login_response, json_rpc_logout_response],
                                                             key=lambda x: x['id'])
        expected_file = Path(tmp_path / '127.0.0.1.recording')
        assert expected_file.exists()
        packets = list(Record.from_file(expected_file))
        assert packets == json_recording_data
        assert expected_file.read_bytes() == json_recording

    @pytest.mark.asyncio
    async def test_02_on_notification_request(self, tmp_path, two_way_receiver_adaptor, json_rpc_login_request_encoded,
                                    json_rpc_logout_request_encoded, timestamp, json_recording, json_recording_data):

    @pytest.mark.parametrize("json_rpc_error_request,json_rpc_error_response_encoded,exception", [
        ('no_version', 'no_version', InvalidRequestError),
        ('wrong_method', 'wrong_method', MethodNotFoundError),
        ('invalid_params', 'invalid_params', InvalidParamsError),
    ], indirect=['json_rpc_error_request', 'json_rpc_error_response_encoded'])
    def test_03_on_exception(self, two_way_receiver_adaptor, json_codec, json_rpc_error_request,
                             json_rpc_error_response_encoded, exception, deque):
        obj = json_codec.from_decoded(json_rpc_error_request)
        two_way_receiver_adaptor._on_exception(exception(), obj)
        msg = deque.pop()
        assert msg == json_rpc_error_response_encoded

    def test_04_response_on_decode_error(self, two_way_receiver_adaptor, invalid_json, json_rpc_parse_error_response_encoded, deque):
        try:
            result = json.loads(invalid_json)
        except JSONDecodeError as e:
            two_way_receiver_adaptor._on_decoding_error(invalid_json, e)
        assert deque.pop() == json_rpc_parse_error_response_encoded



class TestSenderAdaptorTwoWay:
    def test_00_post_init(self, two_way_sender_adaptor, json_codec):
        assert two_way_sender_adaptor.codec == json_codec

    @pytest.mark.asyncio
    async def test_01_close(self, two_way_sender_adaptor):
        await asyncio.wait_for(two_way_sender_adaptor.close_actions(None), timeout=1)

    @pytest.mark.asyncio
    async def test_02_wait_notification(self, two_way_sender_adaptor, json_rpc_create_notification_object):
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(two_way_sender_adaptor.wait_notification(), timeout=1)
        two_way_sender_adaptor._notification_queue.put_nowait(json_rpc_create_notification_object)
        notification = await two_way_sender_adaptor.wait_notification()
        assert notification == json_rpc_create_notification_object

    def test_03_get_notification(self, two_way_sender_adaptor, json_rpc_create_notification_object):
        two_way_sender_adaptor._notification_queue.put_nowait(json_rpc_create_notification_object)
        notification = two_way_sender_adaptor.get_notification()
        assert notification == json_rpc_create_notification_object

    @pytest.mark.asyncio
    async def test_04_all_notifications(self, two_way_sender_adaptor, json_rpc_create_notification_object):
        two_way_sender_adaptor._notification_queue.put_nowait(json_rpc_create_notification_object)
        obj = next(two_way_sender_adaptor.all_notifications())
        assert obj == json_rpc_create_notification_object

    @pytest.mark.asyncio
    async def test_05_process_msgs_response(self, two_way_sender_adaptor, json_rpc_login_response_object, json_rpc_login_response_encoded):
        fut = asyncio.Future()
        two_way_sender_adaptor._scheduler._futures[1] = fut
        two_way_sender_adaptor.process_msgs([json_rpc_login_response_object], json_rpc_login_response_encoded)
        result = await asyncio.wait_for(fut, timeout=1)
        assert result == json_rpc_login_response_object

    @pytest.mark.asyncio
    async def test_06_process_msgs_notification(self, two_way_sender_adaptor, json_rpc_create_notification_object, json_rpc_create_notification_encoded):
        two_way_sender_adaptor.process_msgs([json_rpc_create_notification_object], json_rpc_create_notification_encoded)
        result = await asyncio.wait_for(two_way_sender_adaptor.wait_notification(), timeout=1)
        assert result == json_rpc_create_notification_object

    @pytest.mark.asyncio
    async def test_07_send_data_and_wait(self, two_way_sender_adaptor, json_rpc_login_request_encoded,
                                         json_rpc_login_request,
                                         json_rpc_login_response_object, json_rpc_login_response_encoded, queue):
        task = asyncio.create_task(two_way_sender_adaptor.send_data_and_wait(1, json_rpc_login_request_encoded))
        msg = await queue.get()
        assert json.loads(msg) == json_rpc_login_request
        two_way_sender_adaptor.process_msgs([json_rpc_login_response_object], json_rpc_login_response_encoded)
        result = await asyncio.wait_for(task, timeout=1)
        assert result == json_rpc_login_response_object

    @pytest.mark.asyncio
    async def test_08_send_msg_and_wait(self, two_way_sender_adaptor, json_rpc_login_request, json_rpc_login_request_object,
                                        json_rpc_login_response_object, json_rpc_login_response_encoded, queue):
        task = asyncio.create_task(two_way_sender_adaptor.send_msg_and_wait(json_rpc_login_request_object))
        msg = await queue.get()
        assert json.loads(msg) == json_rpc_login_request
        two_way_sender_adaptor.process_msgs([json_rpc_login_response_object], json_rpc_login_response_encoded)
        result = await asyncio.wait_for(task, timeout=1)
        assert result == json_rpc_login_response_object

    @pytest.mark.asyncio
    async def test_09_encode_send_wait(self, two_way_sender_adaptor, json_rpc_login_request, json_rpc_login_request_encoded,
                                       json_rpc_login_response_object, json_rpc_login_response_encoded, queue):
        task = asyncio.create_task(two_way_sender_adaptor.encode_send_wait(json_rpc_login_request))
        msg = await queue.get()
        assert json.loads(msg) == json_rpc_login_request
        two_way_sender_adaptor.process_msgs([json_rpc_login_response_object], json_rpc_login_response_encoded)
        result = await asyncio.wait_for(task, timeout=1)
        assert result == json_rpc_login_response_object

    @pytest.mark.asyncio
    async def test_10_run_method_and_wait(self, two_way_sender_adaptor, json_rpc_login_request,
                                          json_rpc_login_response_object, json_rpc_login_response_encoded, queue):
        task = asyncio.create_task(two_way_sender_adaptor.login("user1", "password"))
        msg = await queue.get()
        assert json.loads(msg) == json_rpc_login_request
        two_way_sender_adaptor.process_msgs([json_rpc_login_response_object], json_rpc_login_response_encoded)
        result = await asyncio.wait_for(task, timeout=1)
        assert result == json_rpc_login_response_object

    @pytest.mark.asyncio
    async def test_11_run_method(self, two_way_sender_adaptor,json_rpc_subscribe_request, queue):
        two_way_sender_adaptor.subscribe_to_user("user1")
        msg = await queue.get()
        assert json.loads(msg) == json_rpc_subscribe_request

    @pytest.mark.asyncio
    async def test_12_no_method(self, two_way_sender_adaptor,json_rpc_subscribe_request, queue):
        with pytest.raises(MethodNotFoundError):
            two_way_sender_adaptor.subscrbe_to_user("user1")

    @pytest.mark.asyncio
    async def test_13_play_recording_delay(self, two_way_sender_adaptor, file_containing_asn1_recording, buffer_asn1_1,
                                           buffer_asn1_2, deque):
        coro = two_way_sender_adaptor.play_recording(file_containing_asn1_recording, timing=True)
        time_taken = await time_coro(coro)
        assert list(deque) == [buffer_asn1_1, buffer_asn1_2]
        assert time_taken > 1.0
