import asyncio
import logging
import time
import shutil
import multiprocessing
import threading

from lib.basetestcase import BaseTestCase
from lib.senders import tasks
from lib import settings
from lib.run_sender import get_sender

logger = logging.getLogger(settings.LOGGER_NAME)


class BaseReceiverTestCase(BaseTestCase):
    multiple_encoded_hex = (
        b'62474804000000016b1e281c060700118605010101a011600f80020780a1090607040000010014026c1fa11d0201ff02012d30158007911497427533f38101008207911497797908f0',
        b'6581aa4804840001ff4904a50500016b2a2828060700118605010101a01d611b80020780a109060704000001000e03a203020100a305a1030201006c80a26c0201013067020138a380a180305a04104b9d6191107536658cfe59880cd2ac2704104b8c43a2542050120467f333c00f42d804108c43a2542050120467f333c00f42d84b041043a2542050120467f333c00f42d84b8c0410a2551a058cdb00004b8d79f7caff5012000000000000',
        b'65164804a50500014904840001ff6c08a106020102020138',
        b'643c4904571800006b2a2828060700118605010101a01d611b80020780a109060704000001000503a203020100a305a1030201006c08a30602010102010b'
    )
    long_msg = b'62474804000000016b1e281c060700118605010101a011600f80020780a1090607040000010014026c1fa11d0201ff02012d30158007911497427533f38101008207911497797908f06581aa4804840001ff4904a50500016b2a2828060700118605010101a01d611b80020780a109060704000001000e03a203020100a305a1030201006c80a26c0201013067020138a380a180305a04104b9d6191107536658cfe59880cd2ac2704104b8c43a2542050120467f333c00f42d804108c43a2542050120467f333c00f42d84b041043a2542050120467f333c00f42d84b8c0410a2551a058cdb00004b8d79f7caff5012000000000000'
    change_loop_policy = False
    status_change = multiprocessing.Event()
    stop_ordered = multiprocessing.Event()
    config_file = 'tcp_server_test_setup.ini'
    server_as_process = False

    @staticmethod
    def start_server(config_file, change_loop_policy, status_change, stop_ordered):
        settings.CONFIG_ARGS = settings.TEST_CONF_DIR.joinpath(config_file),
        from lib.run_receiver import main
        if change_loop_policy:
            from lib.utils import set_loop_policy
            set_loop_policy()
        asyncio.run(main(status_change=status_change, stop_ordered=stop_ordered), debug=True)

    def start_server_process(self):
        self.process = multiprocessing.Process(target=self.start_server,
                                               args=(self.config_file, self.change_loop_policy, self.status_change, self.stop_ordered))
        self.process.start()
        self.status_change.wait()

    def start_server_thread(self):
        self.thread = threading.Thread(target=self.start_server,
                                        args=(self.config_file, self.change_loop_policy, self.status_change,
                                              self.stop_ordered))
        self.thread.start()
        self.status_change.wait()

    def setUp(self):
        settings.CONFIG_ARGS = settings.TEST_CONF_DIR.joinpath(self.config_file),
        try:
            shutil.rmtree(self.base_data_dir)
        except OSError:
            pass
        if self.server_as_process:
            self.start_server_process()
        else:
            self.start_server_thread()

    def tearDown(self):
        self.status_change.clear()
        self.stop_ordered.set()
        self.status_change.wait()
        if self.server_as_process:
            self.process.terminate()
            self.process.join()
        else:
            self.thread.join()

    @staticmethod
    async def send_one():
        client = get_sender()
        async with client:
            await client.encode_and_send_msgs([('begin', {'otid': b'\x00\x00\x00\x01', 'dialoguePortion': {
            'direct-reference': (0, 0, 17, 773, 1, 1, 1), 'encoding': ('single-ASN1-type', ('DialoguePDU', (
            'dialogueRequest', {'protocol-version': (1, 1), 'application-context-name': (0, 4, 0, 0, 1, 0, 20, 2)})))},
                                                                'components': [('basicROS', ('invoke', {
                                                                    'invokeId': ('present', -1),
                                                                    'opcode': ('local', 45), 'argument': (
                                                                    'RoutingInfoForSM-Arg',
                                                                    {'msisdn': b'\x91\x14\x97Bu3\xf3',
                                                                     'sm-RP-PRI': False,
                                                                     'serviceCentreAddress': b'\x91\x14\x97yy\x08\xf0'})}))]})])
        await asyncio.sleep(3)

    def assertSendOneMsgOk(self, expected_file):
        asyncio.run(self.send_one(), debug=True)
        time.sleep(3)
        self.assertBinaryFileContentsEqual(expected_file,
                                     b'bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0')

    @staticmethod
    async def send_three_clients(msg1, msg2, msg3):
        client1 = get_sender(srcip='127.0.0.1')
        client2 = get_sender(srcip='127.0.0.2')
        client3 = get_sender(srcip='127.0.0.3')
        async with client1, client2, client3:
            await client1.send_hex(msg1)
            await client2.send_hex(msg2)
            await client3.send_hex(msg3)
        await asyncio.sleep(3)

    def assertSendFromThreeClientsOk(self, expected_file1, expected_file2, directory):
        asyncio.run(self.send_three_clients(self.multiple_encoded_hex[0],
                                            self.multiple_encoded_hex[1], self.multiple_encoded_hex[2]))
        time.sleep(2)
        self.assertBinaryFileContentsEqual(expected_file1,
                                     b'bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0')
        self.assertBinaryFileContentsEqual(expected_file2,
                                           b"e\x81\xaaH\x04\x84\x00\x01\xffI\x04\xa5\x05\x00\x01k*((\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x1da\x1b\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x0e\x03\xa2\x03\x02\x01\x00\xa3\x05\xa1\x03\x02\x01\x00l\x80\xa2l\x02\x01\x010g\x02\x018\xa3\x80\xa1\x800Z\x04\x10K\x9da\x91\x10u6e\x8c\xfeY\x88\x0c\xd2\xac'\x04\x10K\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8\x04\x10\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x04\x10C\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x8c\x04\x10\xa2U\x1a\x05\x8c\xdb\x00\x00K\x8dy\xf7\xca\xffP\x12\x00\x00\x00\x00\x00\x00")
        self.assertNumberOfFilesInDirectory(directory, 2)

    async def send_multiple_messages(self):
        client = get_sender(srcip='127.0.0.1')
        async with client:
            await client.send_hex_msgs(self.multiple_encoded_hex)
        await asyncio.sleep(2)

    def assertMultipleMessagesSameSenderOK(self, expected_file, directory):
        asyncio.run(self.send_multiple_messages())
        self.assertBinaryFileContentsEqual(expected_file,
                                           b"bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0e\x81\xaaH\x04\x84\x00\x01\xffI\x04\xa5\x05\x00\x01k*((\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x1da\x1b\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x0e\x03\xa2\x03\x02\x01\x00\xa3\x05\xa1\x03\x02\x01\x00l\x80\xa2l\x02\x01\x010g\x02\x018\xa3\x80\xa1\x800Z\x04\x10K\x9da\x91\x10u6e\x8c\xfeY\x88\x0c\xd2\xac'\x04\x10K\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8\x04\x10\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x04\x10C\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x8c\x04\x10\xa2U\x1a\x05\x8c\xdb\x00\x00K\x8dy\xf7\xca\xffP\x12\x00\x00\x00\x00\x00\x00e\x16H\x04\xa5\x05\x00\x01I\x04\x84\x00\x01\xffl\x08\xa1\x06\x02\x01\x02\x02\x018d<I\x04W\x18\x00\x00k*((\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x1da\x1b\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x05\x03\xa2\x03\x02\x01\x00\xa3\x05\xa1\x03\x02\x01\x00l\x08\xa3\x06\x02\x01\x01\x02\x01\x0b"
                                           )
        self.assertNumberOfFilesInDirectory(directory, 1)
