from lib.conf.parse_args import get_configuration_args
from lib.protocols.contrib.TCAP_MAP import TCAP_MAP_ASNProtocol
from lib.run_manager import start_multiprocess_manager
from lib.run_receiver import main
from lib.utils import set_loop
import definitions


def message_manager_process(queue):
    setup()
    return start_multiprocess_manager(queue)


def setup():
    definitions.CONFIG_ARGS = get_configuration_args()
    definitions.PROTOCOLS = {
        'TCAP': TCAP_MAP_ASNProtocol
    }
    definitions.MESSAGE_MANAGER_PROCESS = message_manager_process


if __name__ == '__main__':
    import asyncio
    set_loop()
    setup()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
