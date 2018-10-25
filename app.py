from lib.conf.parse_args import get_configuration_args
from lib.protocols.contrib.TCAP_MAP import TCAP_MAP_ASNProtocol
from lib.run_receiver import main
from lib.utils import set_loop
import definitions


definitions.PROTOCOLS = {
    'TCAP': TCAP_MAP_ASNProtocol
}


if __name__ == '__main__':
    import asyncio
    set_loop()
    definitions.CONFIG_ARGS = get_configuration_args()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
