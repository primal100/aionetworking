from lib.conf.parser import INIFileConfig
from lib.messagemanagers.managers import MessageManager, BatchMessageManager
from lib.receivers.asyncio_servers import TCPServerReceiver, UDPServerReceiver
from lib.receivers.sftp import SFTPServerPswAuth
from lib.senders.sftp import SFTPClient
from lib.senders.asyncio_clients import TCPClient, UDPClient
from lib.actions import binary, decode, prettify, summarise, text

from typing import Mapping, Union, TYPE_CHECKING, Type

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
MESSAGE_MANAGER: Type[BaseMessageManager] = MessageManager
BATCH_MESSAGE_MANAGER: Type[BaseMessageManager] = BatchMessageManager
PROTOCOLS: Mapping[str, Type[BaseProtocol]] = {}
MESSAGE_MANAGER_PROCESS: function = None
