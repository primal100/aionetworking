from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from aionetworking.compatibility import TypedDict
from aionetworking.utils import ipv4_or_ipv6
import configparser
import datetime
from pathlib import Path
from typing import Tuple, Type, Dict, Union, Any


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


class DistinguishedName(TypedDict):
    C: str
    ST: str
    L: str
    O: str
    OU: str
    CN: str
    emailAddress: str


test_distinguished_name: DistinguishedName = DistinguishedName(C='IE', ST='Dublin', L='Dublin', O='AIONetworking',
                                                               OU='testing', CN='localhost',
                                                               emailAddress='aionetworking@example.com')


def get_name_type(key: str) -> Type[x509.GeneralName]:
    if key.startswith('DNS'):
        return x509.DNSName
    elif key.startswith('IP'):
        return x509.IPAddress
    elif key.startswith('RID'):
        return x509.RegisteredID
    elif key.startswith('DN'):
        return x509.DirectoryName
    raise KeyError(f'{key} is not a valid Alternative Subject Name Type')


def generate_cert(path: Path, private_key: rsa.RSAPrivateKey, validity: int = 365, distinguished_name: DistinguishedName = None,
                  basicConstraints: Dict[str, Union[str, bool]] = None, keyUsage: Dict[str, bool] = None,
                  subjectAltName: [str, str] = None) -> x509.Certificate:
    distinguished_name = distinguished_name or test_distinguished_name
    subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, distinguished_name['C']),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, distinguished_name['ST']),
            x509.NameAttribute(NameOID.LOCALITY_NAME, distinguished_name['L']),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, distinguished_name['O']),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, distinguished_name['O']),
            x509.NameAttribute(NameOID.COMMON_NAME, distinguished_name['CN']),
            x509.NameAttribute(NameOID.EMAIL_ADDRESS, distinguished_name['emailAddress'])
        ])
    cert = x509.CertificateBuilder().subject_name(
    subject
        ).issuer_name(
    issuer
        ).public_key(
    private_key.public_key()
        ).serial_number(
    x509.random_serial_number()
        ).not_valid_before(
    datetime.datetime.utcnow()
        ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=validity)
        )
    if basicConstraints:
        basicConstraints = {key.lower(): True if value is True or value.lower() == 'true' else False for key, value in basicConstraints.items()}
        for key in ('ca', 'path_length'):
            if key not in basicConstraints:
                basicConstraints[key] = None
        cert.add_extension(
            x509.BasicConstraints(**basicConstraints), critical=True,
        )
    if keyUsage:
        key_usage = {
            'crl_sign': keyUsage.get('crlSign', False),
            'data_encipherment': keyUsage.get('dataEncipherment', False),
            'digital_signature': keyUsage.get('digitalSignature', False),
            'content_commitment': keyUsage.get('nonRepudiation', False),
            'key_agreement': keyUsage.get('keyAgreement', False),
            'key_cert_sign': keyUsage.get('keyCertSign', False),
            'key_encipherment': keyUsage.get('keyEncipherment', False),
            'encipher_only': keyUsage.get('encipherOnly', False),
            'decipher_only': keyUsage.get('decipherOnly', False),
        }
        cert.add_extension(
            x509.KeyUsage(**key_usage), critical=True,
        )
    if subjectAltName:
        alt_names = []
        for key, value in subjectAltName.items():
            if key.startswith('IP'):
                value = ipv4_or_ipv6(value)
            san_type = get_name_type(key)
            alt_names.append(san_type(value))
        cert = cert.add_extension(
            x509.SubjectAlternativeName(alt_names), critical=False,
        )
    cert = cert.sign(private_key, hashes.SHA256(), default_backend())
    data = cert.public_bytes(serialization.Encoding.PEM)
    Path(path).write_bytes(data)
    return cert


def generate_signed_key_cert(base_path: Path, privkey_filename='privkey.pem', cert_filename='cert.pem',
                             public_exponent: int = 65537, key_size: int = 2048, passphrase: str = None,
                             validity: int = 365, distinguished_name: DistinguishedName = None,
                             basicConstraints: Dict[str, bool] = None, keyUsage: Dict[str, bool] = None,
                             subjectAltName: [str, str] = None) -> Tuple[x509.Certificate, Path, rsa.RSAPrivateKey, Path]:
    key_path = Path(base_path / privkey_filename)
    cert_path = Path(base_path / cert_filename)
    key = generate_privkey(key_path, public_exponent=public_exponent, key_size=key_size, passphrase=passphrase)
    cert = generate_cert(cert_path, key, validity=validity, distinguished_name=distinguished_name,
                         basicConstraints=basicConstraints, keyUsage=keyUsage, subjectAltName=subjectAltName)
    return cert, cert_path, key, key_path


def read_from_openssl_conf_file(path: Union[Path, str]) -> Dict[str, Any]:
    config = configparser.ConfigParser()
    config.optionxform = str
    with open(path, 'r') as f:
        config.read_file(open(path))
    distinguished_name_section_name = config.get('req', 'distinguished_name')
    distinguished_name = DistinguishedName(**config[distinguished_name_section_name])
    req_extension_section_name = config.get('req', 'req_extension', fallback=None)
    if req_extension_section_name:
        req_extension_section = config[req_extension_section_name]
        basicConstraints = req_extension_section.get('basicConstraints', fallback=None)
        if basicConstraints:
            basic_constraints = {}
            for basic_constraint in basicConstraints.replace(' ', '').split(','):
                key, value = basic_constraint.split(':')
                basic_constraints[key] = value
        else:
            basic_constraints = None
        keyUsage = req_extension_section.get('keyUsage', fallback=None)
        if keyUsage:
            key_usage = {}
            for key in keyUsage.replace(' ', '').split(','):
                key_usage[key] = True
        else:
            key_usage = None
        subject_alt_name = req_extension_section.get('subjectAltName', '')
        if subject_alt_name.startswith('@'):
            subject_alt_names_section_name = subject_alt_name.replace('@', '')
            subject_alt_names = config[subject_alt_names_section_name]
        elif subject_alt_name:
            subject_alt_names = {}
            for alt_name in subject_alt_name.replace(' ', '').split(','):
                key, value = alt_name.split(':')
                subject_alt_names[key] = value
        else:
            subject_alt_names = None
        return dict(distinguished_name=distinguished_name, basicConstraints=basic_constraints,
                    keyUsage=key_usage, subjectAltName=subject_alt_names)
    return dict(distinguished_name=distinguished_name)


def generate_cert_from_openssl_conf_file(conf_path: Union[str, Path], out_path: Path, key: rsa.RSAPrivateKey,
                                         validity: int = 365):
    kwargs = read_from_openssl_conf_file(conf_path)
    return generate_cert(out_path, key, validity=validity, **kwargs)


def generate_signed_key_cert_from_openssl_conf_file(conf_path: Union[str, Path], out_path: Path,
                                                    privkey_filename='privkey.pem', cert_filename='cert.pem',
                                                    public_exponent: int = 65537, key_size: int = 2048,
                                                    passphrase: str = None, validity: int = 365):
    kwargs = read_from_openssl_conf_file(conf_path)
    return generate_signed_key_cert(out_path, privkey_filename=privkey_filename, cert_filename=cert_filename,
                                    public_exponent=public_exponent, key_size=key_size, passphrase=passphrase,
                                    validity=validity, **kwargs)
