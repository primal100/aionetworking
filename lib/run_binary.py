from lib.receivers.asyncio_server import InterfaceServer
from lib.actions import binary, decode, prettify, summarise
from lib.interfaces.contrib.TCAP_MAP import TCAP_MAP_ASNInterface
from lib.configuration.parser import ConfigParserConfig
from lib.run import start
import os

APP_NAME = 'pymessagemanager'
message_manager = MessageManager
batch_message_manager = BatchMessageManager

receivers = {
    'server': InterfaceServer
}
actions = {
    'binary': binary,
    'decode': decode,
    'prettify': prettify,
    'summarise': summarise
}

interfaces = {
    'TCAP': TCAP_MAP_ASNInterface
}

config_meta = {
    'filename': os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "message_manager.cfg")
    }

config = parser(config_meta)

if __name__ == '__main__':
    start(APP_NAME, receivers, actions, interfaces, config)

