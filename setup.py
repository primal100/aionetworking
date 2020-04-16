from setuptools import setup
from setuptools.command.develop import develop as develop_orig
from pathlib import Path

from aionetworking_package import get_requirements, libsystemd_is_installed


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
    packages=['aionetworking', 'aionetworking_package'],
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
