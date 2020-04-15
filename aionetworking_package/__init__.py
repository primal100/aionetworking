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
