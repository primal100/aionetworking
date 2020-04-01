import ssl
import pytest


class TestSSL:

    @pytest.mark.connections('tcp_oneway_all')
    def test_00_get_ssl_context(self, ssl_context):
        context = ssl_context.context
        assert context.check_hostname is True
        assert context.verify_mode == ssl.CERT_REQUIRED

    def test_01_no_ssl(self, server_side_no_ssl):
        context = server_side_no_ssl.context
        assert context is None
