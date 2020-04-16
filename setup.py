from setuptools import setup

import platform
from pathlib import Path
from pkg_resources import parse_requirements

from typing import List, Union


def get_requirements(filename: Union[str, Path]) -> List[str]:
    text = Path(filename).read_text()
    return [str(requirement) for requirement in parse_requirements(text)]


def linux_package_is_installed(*package_names: str) -> bool:
    try:
        import apt
        cache = apt.Cache()
        return all(cache.get(package) and cache[package].is_installed for package in package_names)
    except ImportError:
        try:
            import yum
            yb = yum.YumBase()
            return all(yb.rpmdb.searchNevra(name=package) for package in package_names)
        except ImportError:
            return False


def libsystemd_is_installed() -> bool:
    if platform.system() == 'Linux':
        return linux_package_is_installed('libsystemd-dev')
    return False


readme = Path('README.md').read_text()
pkg_license = Path('LICENSE').read_text()


required = get_requirements('requirements.txt')
if libsystemd_is_installed():
    required += get_requirements('requirements_systemd.txt')
optional = get_requirements('requirements_optional.txt')
sftp_requirements = get_requirements('requirements_sftp.txt')


setup(
    name='aionetworking',
    version='0.1',
    packages=['aionetworking', 'aionetworking.conf', 'aionetworking.types', 'aionetworking.actions',
              'aionetworking.formats', 'aionetworking.formats.contrib', 'aionetworking.futures',
              'aionetworking.logging', 'aionetworking.senders', 'aionetworking.receivers', 'aionetworking.networking',
              'aionetworking.requesters'],
    scripts=['scripts/generate_ssh_host_key.py'],
    url='https://github.com/primal100/aionetworking',
    license=pkg_license,
    author='Paul Martin',
    author_email='greatestloginnameever@gmail.com',
    description='Various utilities for asyncio networking',
    long_description=readme,
    classifiers=[
        'Development Status :: 4 - Beta'
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Framework :: AsyncIO'
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',

    ],
    python_requires='>=3.6',
    setup_requires=['wheel'],
    install_requires=required,
    extras_require={
        'sftp': sftp_requirements,
        'optional': optional,
        'all': sftp_requirements + optional
    },
)
