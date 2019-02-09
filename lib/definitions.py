from lib.conf.parser import INIFileConfig
from lib.conf.log_filters import BaseFilter, SenderFilter, MessageFilter
from lib.messagemanagers.managers import OneWayMessageManager, ClientMessageManager
from lib.receivers.asyncio_servers import TCPServerReceiver, UDPServerReceiver
from lib.receivers.sftp import SFTPServerPswAuth
from lib.senders.sftp import SFTPClient
from lib.senders.asyncio_clients import TCPClient, UDPClient
from lib.actions import FileStorage, BufferedFileStorage

from typing import Mapping, Union, TYPE_CHECKING, Type

if TYPE_CHECKING:
    from lib.actions import BaseAction
    from lib.conf import BaseConfigClass
    from lib.messagemanagers import BaseMessageManager
    from lib.protocols import BaseProtocol
    from lib.receivers import BaseReceiver
    from lib.senders import BaseSender
else:
    BaseAction = None
    BaseConfigClass = None
    BaseMessageManager = None
    BaseProtocol = None
    BaseReceiver = None
    BaseSender = None
    Queue = None

CONFIG_CLS: Type[BaseConfigClass] = INIFileConfig
RECEIVERS: Mapping[str, Mapping[str, Union[Type[BaseReceiver], Type[BaseSender]]]] = {
    'TCPServer': {'receiver': TCPServerReceiver, 'sender': TCPClient},
    'UDPServer': {'receiver': UDPServerReceiver, 'sender': UDPClient},
    'SFTPServer':  {'receiver': SFTPServerPswAuth, 'sender': SFTPClient},
}
ACTIONS: Mapping[str, Type[BaseAction]] = {
    'filestorage': FileStorage,
    'bufferedfilestorage': BufferedFileStorage
}
LOG_FILTERS: Mapping[str, Type[BaseFilter]] = {
    'sender_filter': SenderFilter,
    'message_filter': MessageFilter
}
MESSAGE_MANAGER: Type[BaseMessageManager] = OneWayMessageManager
CLIENT_MESSAGE_MANAGER: Type[BaseMessageManager] = ClientMessageManager
PROTOCOLS: Mapping[str, Type[BaseProtocol]] = {}
