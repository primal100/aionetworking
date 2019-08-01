import pytest
import asyncio
from datetime import timedelta
from pathlib import Path
import json
from json.decoder import JSONDecodeError

from lib.actions.jsonrpc import InvalidRequestError, MethodNotFoundError, InvalidParamsError
from lib.utils import Record, alist, time_coro


class TestTwoWayReceiverAdaptor:
    def test_00_post_init(self, two_way_receiver_adaptor, json_codec):
        assert two_way_receiver_adaptor.codec == json_codec

    @pytest.mark.asyncio
    async def test_01_close(self, two_way_receiver_adaptor):
        await two_way_receiver_adaptor.close(None, timeout=0.1)

    @pytest.mark.asyncio
    async def test_02_manage_buffer(self, tmp_path, two_way_receiver_adaptor, json_rpc_login_request_encoded,
                                    json_rpc_logout_request_encoded, timestamp, json_recording, json_recording_data):
        two_way_receiver_adaptor._manage_buffer(json_rpc_login_request_encoded, timestamp)
        two_way_receiver_adaptor._manage_buffer(json_rpc_logout_request_encoded, timestamp + timedelta(seconds=1))
        await two_way_receiver_adaptor.close(None, timeout=0.5)
        expected_file = Path(tmp_path / '127.0.0.1.recording')
        assert expected_file.exists()
        packets = list(Record.from_file(expected_file))
        assert packets == json_recording_data
        assert expected_file.read_bytes() == json_recording

    def test_03_on_success_with_message(self, two_way_receiver_adaptor, json_rpc_login_request_object, json_rpc_login_response,
                                        json_rpc_login_response_encoded, deque):
        two_way_receiver_adaptor._on_success(json_rpc_login_response, json_rpc_login_request_object)
        msg = deque.pop()
        assert msg == json_rpc_login_response_encoded

    def test_04_on_success_no_message(self, two_way_receiver_adaptor, json_rpc_login_request_object,
                                      json_rpc_login_response, deque):
        two_way_receiver_adaptor._on_success(None, json_rpc_login_request_object)
        with pytest.raises(IndexError):
            deque.pop()

    @pytest.mark.parametrize("json_rpc_error_request,json_rpc_error_response_encoded,exception", [
        ('no_version', 'no_version', InvalidRequestError),
        ('wrong_method', 'wrong_method', MethodNotFoundError),
        ('invalid_params', 'invalid_params', InvalidParamsError),
    ], indirect=['json_rpc_error_request', 'json_rpc_error_response_encoded'])
    def test_05_on_exception(self, two_way_receiver_adaptor, json_codec, json_rpc_error_request,
                             json_rpc_error_response_encoded, exception, deque):
        obj = json_codec.from_decoded(json_rpc_error_request)
        two_way_receiver_adaptor._on_exception(exception(), obj)
        msg = deque.pop()
        assert msg == json_rpc_error_response_encoded

    def test_06_response_on_decode_error(self, two_way_receiver_adaptor, invalid_json, json_rpc_parse_error_response_encoded, deque):
        try:
            result = json.loads(invalid_json)
        except JSONDecodeError as e:
            two_way_receiver_adaptor._on_decoding_error(invalid_json, e)
        assert deque.pop() == json_rpc_parse_error_response_encoded

    @pytest.mark.asyncio
    async def test_07_process_msgs(self, two_way_receiver_adaptor, json_buffer, timestamp, json_codec, json_rpc_login_response,
                                   json_rpc_logout_response, json_rpc_login_request_object, json_rpc_logout_request_object, deque):
        two_way_receiver_adaptor.process_msgs([json_rpc_login_request_object, json_rpc_logout_request_object], json_buffer)
        await two_way_receiver_adaptor.close(None, timeout=0.5)
        msg1 = deque.pop()
        msg2 = deque.pop()
        msgs = [json.loads(msg1), json.loads(msg2)]
        assert sorted(msgs, key=lambda x: x['id']) == sorted([json_rpc_login_response, json_rpc_logout_response],
                                                             key=lambda x: x['id'])

    @pytest.mark.asyncio
    async def test_08_on_data_received(self, tmp_path, two_way_receiver_adaptor, json_rpc_login_request_encoded,
                                       json_rpc_logout_request_encoded, json_rpc_login_response,
                                       json_rpc_logout_response, timestamp, json_recording, json_recording_data, deque):
        two_way_receiver_adaptor.on_data_received(json_rpc_login_request_encoded, timestamp)
        two_way_receiver_adaptor.on_data_received(json_rpc_logout_request_encoded, timestamp + timedelta(seconds=1))
        await two_way_receiver_adaptor.close(None, timeout=0.5)
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


class TestSenderAdaptorTwoWay:
    def test_00_post_init(self, two_way_sender_adaptor, json_codec):
        assert two_way_sender_adaptor.codec == json_codec

    @pytest.mark.asyncio
    async def test_01_close(self, two_way_sender_adaptor):
        await two_way_sender_adaptor.close(None, timeout=0.1)

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

    def test_05_send_hex_msgs(self, one_way_sender_adaptor, asn_encoded_hex, asn_encoded_multi, deque):
        one_way_sender_adaptor.send_hex_msgs(asn_encoded_hex)
        assert list(deque) == asn_encoded_multi

    def test_06_encode_msg(self, one_way_sender_adaptor, asn_one_decoded, asn_object):
        encoded_msg = one_way_sender_adaptor.encode_msg(asn_one_decoded)
        assert encoded_msg == asn_object

    def test_07_encode_and_send_msg(self, one_way_sender_adaptor, asn_one_decoded, asn_one_encoded, deque):
        one_way_sender_adaptor.encode_and_send_msg(asn_one_decoded)
        assert deque.pop() == asn_one_encoded

    def test_08_encode_and_msgs(self, one_way_sender_adaptor, asn_decoded_multi, asn_encoded_multi, deque):
        one_way_sender_adaptor.encode_and_send_msgs(asn_decoded_multi)
        assert list(deque) == asn_encoded_multi

    @pytest.mark.asyncio
    async def test_09_play_recording(self, one_way_sender_adaptor, file_containing_asn1_recording, buffer_asn1_1, buffer_asn1_2, deque):
        await asyncio.wait_for(one_way_sender_adaptor.play_recording(file_containing_asn1_recording, timing=False),
                               timeout=0.1)
        assert list(deque) == [buffer_asn1_1, buffer_asn1_2]

    @pytest.mark.asyncio
    async def test_10_play_recording_delay(self, one_way_sender_adaptor, file_containing_asn1_recording, buffer_asn1_1,
                                           buffer_asn1_2, deque):
        coro = one_way_sender_adaptor.play_recording(file_containing_asn1_recording, timing=True)
        time_taken = await time_coro(coro)
        assert list(deque) == [buffer_asn1_1, buffer_asn1_2]
        assert time_taken > 1.0
