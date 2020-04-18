import asyncio
import datetime
import ssl
import pytest
from aionetworking.networking.ssl import check_peercert_expired


class TestSSL:

    @pytest.mark.connections('tcp_oneway_all')
    @pytest.mark.asyncio
    async def test_00_get_ssl_context(self, ssl_context):
        context = ssl_context.context
        assert context.check_hostname is False
        assert context.verify_mode == ssl.CERT_REQUIRED

    def test_01_no_ssl(self, server_side_no_ssl):
        context = server_side_no_ssl.context
        assert context is None

    @pytest.mark.asyncio
    async def test_02_cert_about_to_expire(self, server_side_ssl_short_validity, short_validity_cert_actual_expiry_time,
                                           caplog):
        context = server_side_ssl_short_validity.context
        await asyncio.sleep(0)
        expected_msg = f'Own ssl cert will expire in less than 3 days, on {short_validity_cert_actual_expiry_time}'
        assert expected_msg in caplog.messages

    @pytest.mark.asyncio
    async def test_03_cert_not_about_to_expire(self, server_side_ssl_long_validity, caplog):
        context = server_side_ssl_long_validity.context
        await asyncio.sleep(0)
        assert not any('Own ssl cert' in message for message in caplog.messages)

    @pytest.mark.asyncio
    async def test_04_check_peercert_expires_soon(self, peercert_expires_soon):
        expiry_time, days = check_peercert_expired(peercert_expires_soon, 7)
        assert expiry_time == datetime.datetime(2019, 1, 2, 11, 13, 58)
        assert days == 1

    @pytest.mark.asyncio
    async def test_05_check_peercert_not_expired(self, peercert):
        expiry_time, days = check_peercert_expired(peercert, 7)
        assert expiry_time == datetime.datetime(2030, 3, 6, 11, 13, 58)
        assert days is None
