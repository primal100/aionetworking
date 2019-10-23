import ssl


class TestSSL:

    def test_00_get_ssl_server_context(self, ssl_object):
        context = ssl_object.context
        assert context.check_hostname is True
        assert context.verify_mode == ssl.CERT_REQUIRED

    def test_01_no_ssl(self, server_side_no_ssl):
        context = server_side_no_ssl.context
        assert context is None