import inspect
from ipaddress import IPv4Network, IPv6Network, _BaseNetwork
from pydantic.types import change_exception
from pydantic.errors import PydanticValueError

from typing import TYPE_CHECKING, Any, Generator, Type, Union, Tuple

if TYPE_CHECKING:
    from pydantic.utils import AnyCallable

    CallableGenerator = Generator[AnyCallable, None, None]

NetworkType = Union[str, bytes, int, Tuple[Union[str, bytes, int], Union[str, int]]]


AnyType = Type[Any]


class IPvAnyNetworkError(PydanticValueError):
    msg_template = 'value is not a valid IPv4 or IPv6 network'


class IPvAnyNetwork(_BaseNetwork):  # type: ignore
    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield cls.validate

    @classmethod
    def validate(cls, value: NetworkType) -> Union[IPv4Network, IPv6Network]:
        # Assume IP Network is defined with a default value for ``strict`` argument.
        # Define your own class if you want to specify network address check strictness.
        try:
            return IPv4Network(value)
        except ValueError:
            pass

        with change_exception(IPvAnyNetworkError, ValueError):
            return IPv6Network(value)
