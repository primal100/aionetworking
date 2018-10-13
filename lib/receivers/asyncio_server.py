import asyncio
import ssl
import signal
import os
import logging.config

from lib.interfaces import supported_interfaces
from mcmessagemanagers.messagemanagers import MessageManager, BatchMessageManager

from lib import utils

APPNAME = "TESTMC"


class MCServerException(Exception):
    pass


class HandoverInterfaceNotFoundException(Exception):
    pass


class InterfaceServer:
    def __init__(self, host, port, interface, appdir, sslcert=None, sslkey=None, actions=(),
                 printhex=False, batch=False, allowed_senders=(), loop=None):

        self.host = host
        self.port = port

        self.appdir = appdir
        os.makedirs(self.appdir)
        self.datadir = os.path.join(self.appdir, "data")
        self.logsdir = os.path.join(self.appdir, "logs")

        logging.debug("Data directory: " + self.datadir)
        logging.debug("Logs directory: " + self.logsdir)

        os.makedirs(self.datadir)
        os.makedirs(self.logsdir)

        self.ssl_context = self.manage_ssl_params(sslcert, sslkey)

        try:
            interface = supported_interfaces[interface]
        except KeyError:
            msg = "Supported interfaces are %s" % supported_interfaces.keys()
            logger.error("%s is not a supported interface")
            logger.error(msg)
            raise HandoverInterfaceNotFoundException(msg)

        self.loop = loop or asyncio.get_event_loop()

        manager_cls = self.get_message_manager_cls(batch)
        self.manager = manager_cls(interface, self.appdir, self.datadir, actions=actions, print_hex=printhex,
                                   allowed_senders=allowed_senders, loop=self.loop)

        self.run()

        signal.signal(signal.SIGINT, self.close)
        signal.signal(signal.SIGTERM, self.close)

    @staticmethod
    def manage_ssl_params(sslcert, sslkey):
        if sslcert and sslkey:
            logger.info("Setting up SSL")
            logger.info("Using SSL Cert: " + sslcert)
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(sslcert, sslkey)
            logger.info("SSL Context loaded")
            return ssl_context
        elif sslcert or sslkey:
            msg = "To enable ssl, both --sslcert and --sslkey must be selected"
            logger.error(msg)
            raise MCServerException(msg)
        else:
            logger.info("SSL is not enabled")
            return None

    @staticmethod
    def get_message_manager_cls(batch):
        if batch:
            return BatchMessageManager
        else:
            return MessageManager

    async def handle_packet(self, reader, writer):
        data = await reader.read(100)
        message = data.decode()
        sender = writer.get_extra_info('peername')
        logger.debug("Received msg from " + sender)
        await self.manager.manage(sender, message)

    async def wait_queue_processed(self):
        logger.debug("Checking if task queue is processed before stopping server")
        await self.manager.done()

    def close(self):
        logger.info('Closing server running on %s:%s' % (self.host, self.port))
        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())
        self.loop.run_until_complete(self.wait_queue_processed())
        logger.info("Stopping event loop")
        self.loop.close()
        logging.info('Server closed')

    def run(self):
        logger.info('Starting server on %s:%s' % (self.host, self.port))
        coro = asyncio.start_server(self.handle_packet, self.host, self.port, ssl=self.ssl_context, loop=self.loop)
        self.server = self.loop.run_until_complete(coro)

        print('Serving on {}'.format(self.server.sockets[0].getsockname()))

        try:
            logger.info('Starting event loop')
            self.loop.run_forever()
        except KeyboardInterrupt as e:
            logging.info('Keyboard Interrupt received: ' + str(e), exc_info=False)

        self.close()


def get_option(envvar, default):
    full_envar_name = "%s_%s" % (APPNAME, envvar)
    value = os.environ.get(full_envar_name, default)
    logger.debug("Environment variable %s has value %s" % (full_envar_name, value))
    return value

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Launch ETSI/3GPP LI Interface Listener.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i, --interface',
                        default=supported_interfaces.keys()[0],
                        action='store',
                        nargs='?',
                        choices=supported_interfaces.keys(),
                        help='Select which interface standard to use')
    parser.add_argument('-h, --host', action='store', default=get_option('HOST', '0.0.0.0'),
                        help='Host to listen on')
    parser.add_argument('-p, --port', action='store', default=40000,
                        help='Port to listen')
    parser.add_argument('--sslcert', action="store", default=get_option("SSLCERT", None),
                        help='Path to an ssl cert, if required')
    parser.add_argument('--sslkey', action="store_true", default=get_option("SSLKEY", None),
                        help='Path to ssl keyfile, if required')
    parser.add_argument('-p, --print', action="store_true",
                        help='Print decoded data to stdout')
    parser.add_argument('--summary', action="store_true",
                        help='Store summaries of each file received in one file for each day')
    parser.add_argument('-s, --store', action="store_true",
                        help='Store data in file system')
    parser.add_argument('-b, --batch', action="store_true",
                        help='Concatenate data in a single file where possible')
    parser.add_argument('-d, --dir', action="store", default=get_option("DATADIR", utils.data_directory(APPNAME)),
                        help='Concatenate all data belonging to a single CIN in one file')
    parser.add_argument('-l, --logconfig', action="store", default=get_option("LOGDIR", "logs/hi2_logging.conf"),
                        help='Configuration file for logging')

    args = parser.parse_args()

    logging.config.fileConfig(args.logconfig)
    logger = logging.getLogger()

    logger.debug("Script run with args:")
    logger.debug(args)

    InterfaceServer(args.host, args.port, args.interface, args.dir, sslcert=args.sslcert, sslkey=args.sslkey,
                    actions=args.actions, batch=args.batch)