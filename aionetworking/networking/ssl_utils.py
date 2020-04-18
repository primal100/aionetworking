from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from aionetworking.compatibility import TypedDict
import datetime
from pathlib import Path
from typing import Tuple


def load_cert_file(cert: Path) -> x509.Certificate:
    pem_data = cert.read_bytes()
    return x509.load_pem_x509_certificate(pem_data, default_backend())


def load_cert_expiry_time(cert: Path) -> datetime.datetime:
    cert_data = load_cert_file(cert)
    return cert_data.not_valid_after


def generate_privkey(path: Path = None, public_exponent: int = 65537, key_size: int = 2048, passphrase: str = None) -> \
        rsa.RSAPrivateKeyWithSerialization:
    key = rsa.generate_private_key(
        public_exponent=public_exponent,
        key_size=key_size,
        backend=default_backend()
    )
    if passphrase:
        encryption_algorithm = serialization.BestAvailableEncryption(passphrase.encode())
    else:
        encryption_algorithm = serialization.NoEncryption()
    data = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=encryption_algorithm
    )
    if path:
        path.write_bytes(data)
    return key


class CertData(TypedDict):
    country: str
    state_or_province: str
    locality: str
    organization: str
    common_name: str


test_cert_data: CertData = CertData(country='IE', state_or_province='Dublin', locality='Dublin', organization='testing',
                                    common_name='testing')


def generate_cert(path: Path, key: rsa.RSAPrivateKey, validity: int = 365, dns_name='localhost',
                  cert_data: CertData = None) -> x509.Certificate:
    cert_data = cert_data or test_cert_data
    subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, cert_data['country']),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, cert_data['state_or_province']),
            x509.NameAttribute(NameOID.LOCALITY_NAME, cert_data['locality']),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, cert_data['organization']),
            x509.NameAttribute(NameOID.COMMON_NAME, cert_data['common_name']),
        ])
    cert = x509.CertificateBuilder().subject_name(
    subject
        ).issuer_name(
    issuer
        ).public_key(
    key.public_key()
        ).serial_number(
    x509.random_serial_number()
        ).not_valid_before(
    datetime.datetime.utcnow()
        ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=validity)
        ).add_extension(
    x509.SubjectAlternativeName([x509.DNSName(dns_name)]),
        critical=False,
    ).sign(key, hashes.SHA256(), default_backend())
    data = cert.public_bytes(serialization.Encoding.PEM)
    Path(path).write_bytes(data)
    return cert


def generate_signed_key_cert(base_path: Path, privkey_filename='privkey.pem', cert_filename='cert.pem',
                             public_exponent: int = 65537, key_size: int = 2048, passphrase: str = None,
                             validity: int = 365, cert_data: CertData = None,
                             dns_name: str = 'localhost') -> Tuple[x509.Certificate, Path, rsa.RSAPrivateKey, Path]:
    key_path = Path(base_path / privkey_filename)
    cert_path = Path(base_path / cert_filename)
    key = generate_privkey(key_path, public_exponent=public_exponent, key_size=key_size, passphrase=passphrase)
    cert = generate_cert(cert_path, key, validity=validity, dns_name=dns_name, cert_data=cert_data)
    return cert, cert_path, key, key_path
