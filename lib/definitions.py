from lib.conf.parser import INIFileConfig
from lib.conf.log_filters import BaseFilter, SenderFilter, MessageFilter
from lib.messagemanagers.managers import MessageManager, ClientMessageManager
from lib import run_manager
from lib.receivers.asyncio_servers import TCPServerReceiver, UDPServerReceiver
from lib.receivers.sftp import SFTPServerPswAuth
from lib.senders.sftp import SFTPClient
from lib.senders.asyncio_clients import TCPClient, UDPClient
from lib.actions import binary, decode, prettify, summarise, text

from typing import Mapping, Union, TYPE_CHECKING, Type, Callable

if TYPE_CHECKING:
    from lib.actions.base import BaseAction
    from lib.conf.base import BaseConfigClass
    from lib.messagemanagers.base import BaseMessageManager
    from lib.protocols.base import BaseProtocol
    from lib.receivers.base import BaseReceiver
    from lib.senders.base import BaseSender
else:
    BaseAction = None
    BaseConfigClass = None
    BaseMessageManager = None
    BaseProtocol = None
    BaseReceiver = None
    BaseSender = None
    Queue = None
    Task = None

CONFIG_CLS: Type[BaseConfigClass] = INIFileConfig
RECEIVERS: Mapping[str, Mapping[str, Union[Type[BaseReceiver], Type[BaseSender]]]] = {
    'TCPServer': {'receiver': TCPServerReceiver, 'sender': TCPClient},
    'UDPServer': {'receiver': UDPServerReceiver, 'sender': UDPClient},
    'SFTPServer':  {'receiver': SFTPServerPswAuth, 'sender': SFTPClient},
}
ACTIONS: Mapping[str, Type[BaseAction]] = {
    'binary': binary.Action,
    'decode': decode.Action,
    'prettify': prettify.Action,
    'summarise': summarise.Action,
    'text': text.Action
}
LOG_FILTERS: Mapping[str, Type[BaseFilter]] = {
    'sender_filter': SenderFilter,
    'message_filter': MessageFilter
}
MESSAGE_MANAGER: Type[BaseMessageManager] = MessageManager
CLIENT_MESSAGE_MANAGER: Type[BaseMessageManager] = ClientMessageManager
PROTOCOLS: Mapping[str, Type[BaseProtocol]] = {}
START_MESSAGE_MANAGER_PROCESS: Callable = run_manager.start_manager_as_process
