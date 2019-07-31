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
    async def test_02_manage_buffer(self, tmp_path, two_way_receiver_adaptor, json_encoded_multi, timestamp,
                                    json_recording, json_recording_data):
        two_way_receiver_adaptor._manage_buffer(json_encoded_multi[0], timestamp)
        two_way_receiver_adaptor._manage_buffer(json_encoded_multi[1], timestamp + timedelta(seconds=1))
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
        msgs = [json.loads(msg1), json.loads(msg2)] == [json_rpc_login_response, json_rpc_logout_response]

    @pytest.mark.asyncio
    async def test_04_on_data_received(self, tmp_path, one_way_receiver_adaptor, asn_buffer, buffer_asn1_1,
                                       buffer_asn1_2, timestamp, asn1_recording, asn1_recording_data, asn_codec,
                                       asn_objects):
        one_way_receiver_adaptor.on_data_received(buffer_asn1_1, timestamp)
        one_way_receiver_adaptor.on_data_received(buffer_asn1_2, timestamp + timedelta(seconds=1))
        await one_way_receiver_adaptor.close(None, timeout=0.5)
        expected_file = Path(tmp_path/'Encoded/127.0.0.1_TCAP_MAP.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_buffer
        msgs = await alist(asn_codec.from_file(expected_file))
        assert msgs == asn_objects
        expected_file = Path(tmp_path / '127.0.0.1.recording')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn1_recording
        packets = list(Record.from_file(expected_file))
        assert packets == asn1_recording_data


class TestSenderAdaptorTwoWay:
    def test_00_post_init(self, one_way_receiver_adaptor, asn_codec):
        assert one_way_receiver_adaptor.codec == asn_codec

    @pytest.mark.asyncio
    async def test_01_close(self, one_way_receiver_adaptor):
        await one_way_receiver_adaptor.close(None, timeout=0.1)

    def test_02_send(self, one_way_sender_adaptor, asn_one_encoded, deque):
        one_way_sender_adaptor.send(asn_one_encoded)
        assert deque.pop() == asn_one_encoded

    def test_03_send_data(self, one_way_sender_adaptor, asn_one_encoded, deque):
        one_way_sender_adaptor.send_data(asn_one_encoded)
        assert deque.pop() == asn_one_encoded

    def test_04_send_hex(self, one_way_sender_adaptor, asn_encoded_hex, asn_one_encoded, deque):
        one_way_sender_adaptor.send_hex(asn_encoded_hex[0])
        assert deque.pop() == asn_one_encoded

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
