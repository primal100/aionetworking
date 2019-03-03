import ssl

from pathlib import Path
from typing import Optional


def manage_ssl_params(purpose, context, cert: Path, key: Path, sslkeypassword: str, cafile: Path, capath: Path,
                      cadata: str, certrequired: bool, hostnamecheck: bool, logger) -> Optional[ssl.SSLContext]:
    if context:
        logger.info("Setting up SSL")
        if context is True:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            if cert and key:
                logger.info("Using SSL Cert: %s", cert)
                context.load_cert_chain(str(cert), str(key), password=sslkeypassword)

            context.verify_mode = ssl.CERT_REQUIRED if certrequired else ssl.CERT_NONE
            context.check_hostname = hostnamecheck

            if context.verify_mode != ssl.CERT_NONE:
                if cafile or capath or cadata:
                    locations = {'cafile': str(cafile) if cafile else None,
                                 'capath': str(capath) if capath else None,
                                 'cadata': cadata}
                    context.load_verify_locations(**locations)
                    logger.info("Verifying SSL certs with: %s", locations)
                else:
                    context.load_default_certs(purpose)
                    logger.info("Verifying SSL certs with: %s", ssl.get_default_verify_paths())
        logger.info("SSL Context loaded")
        return context
    else:
        logger.info("SSL is not enabled")
        return None


def get_server_context(*args, **kwargs):
    return manage_ssl_params(ssl.Purpose.CLIENT_AUTH, *args, **kwargs)


def get_client_context(*args, **kwargs):
    return manage_ssl_params(ssl.Purpose.SERVER_AUTH, *args, **kwargs)
