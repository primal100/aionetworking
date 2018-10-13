from lib.receivers.asyncio_server import InterfaceServer
from lib.messagemanagers import BatchMessageManager, MessageManager
from lib.actions import binary, decode, prettify, summarise
from lib.interfaces.contrib.TCAP_MAP import TCAP_MAP_ASNInterface
from lib.run import start
import os


message_manager = MessageManager
batch_message_manager = BatchMessageManager

receivers = {
    'server': InterfaceServer
}
actions = {
    'binary': binary,
    'decode': decode,
    'prettify' prettify,
    'summarise': summarise
}

interfaces = {
    'TCAP': TCAP_MAP_ASNInterface
}

config = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "message_manager.cfg")

if __name__ == '__main__':
    start(message_manager, batch_message_manager, receivers, actions, interfaces, config)

