from lib.conf.parser import INIFileConfig
from lib.conf.log_filters import BaseFilter, SenderFilter, MessageFilter
from lib.receivers.asyncio_servers import TCPServer, UDPServer
from lib.receivers.directory_monitor import DirectoryMonitor
from lib.receivers.sftp import SFTPServerPswAuth
from lib.senders.sftp import SFTPClient
from lib.senders.asyncio_clients import TCPClient, UDPClient
from lib.actions import FileStorage, BufferedFileStorage, Recording

from typing import Mapping, Union, TYPE_CHECKING, Type

if TYPE_CHECKING:
    from lib.actions import BaseReceiverAction
    from lib.conf.base import BaseConfig
    from lib.formats.base import BaseMessageObject
    from lib.receivers import BaseReceiver
    from lib.requesters.base import BaseRequester
    from lib.senders import BaseSender
else:
    BaseAction = None
    BaseConfigClass = None
    BaseMessageManager = None
    BaseProtocol = None
    BaseReceiver = None
    BaseRequester = None
    BaseSender = None
    Queue = None

CONFIG_CLS: Type[BaseConfig] = INIFileConfig
RECEIVERS: Mapping[str, Mapping[str, Union[Type[BaseReceiver], Type[BaseSender]]]] = {
    'TCPServer': {'receiver': TCPServer, 'sender': TCPClient},
    'UDPServer': {'receiver': UDPServer, 'sender': UDPClient},
    'SFTPServer':  {'receiver': SFTPServerPswAuth, 'sender': SFTPClient},
    'DirectoryMonitor': {'receiver': DirectoryMonitor},
}
ACTIONS: Mapping[str, Type[BaseReceiverAction]] = {
    'filestorage': FileStorage,
    'bufferedfilestorage': BufferedFileStorage,
    'record': Recording
}
LOG_FILTERS: Mapping[str, Type[BaseFilter]] = {
    'sender_filter': SenderFilter,
    'message_filter': MessageFilter
}
DATA_FORMATS: Mapping[str, Type[BaseMessageObject]] = {}
REQUESTERS: Mapping[str, Type[BaseRequester]] = {}