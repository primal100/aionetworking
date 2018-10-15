from lib.basetestcase import BaseTestCase
from lib.messagemanagers import BatchMessageManager, MessageFromNotAuthorizedHost
from lib.interfaces.contrib.TCAP_MAP import TCAP_MAP_ASNInterface
from lib.actions import binary, decode, prettify, summarise
from lib import utils
import asyncio
import binascii
import shutil
import os


class TestMessageManager(BaseTestCase):
    sender = '10.10.10.10'
    interface = TCAP_MAP_ASNInterface
    multiple_encoded_hex = (
        b'62474804000000016b1e281c060700118605010101a011600f80020780a1090607040000010014026c1fa11d0201ff02012d30158007911497427533f38101008207911497797908f0',
        b'6581aa4804840001ff4904a50500016b2a2828060700118605010101a01d611b80020780a109060704000001000e03a203020100a305a1030201006c80a26c0201013067020138a380a180305a04104b9d6191107536658cfe59880cd2ac2704104b8c43a2542050120467f333c00f42d804108c43a2542050120467f333c00f42d84b041043a2542050120467f333c00f42d84b8c0410a2551a058cdb00004b8d79f7caff5012000000000000',
        b'65164804a50500014904840001ff6c08a106020102020138',
        b'643c4904571800006b2a2828060700118605010101a01d611b80020780a109060704000001000503a203020100a305a1030201006c08a30602010102010b'
    )

    def setUp(self):

        try:
            shutil.rmtree(os.path.join(self.base_home))
        except OSError:
            pass

        action_modules = {
            'binary': binary,
            'decode': decode,
            'prettify': prettify,
            'summarise': summarise
        }

        self.loop = asyncio.get_event_loop()

        config = self.prepare_config()
        config.config.set('Aliases', self.sender, 'Primary')
        config.config.set('MessageManager', 'GenerateTimestamp', 'True')
        self.msgs = [binascii.unhexlify(encoded_hex) for encoded_hex in self.multiple_encoded_hex]
        self.manager = BatchMessageManager('PyMessageTest', self.interface, action_modules, config, loop=self.loop)

    def test_01_allowed_sender(self):
        host = self.manager.check_sender('10.10.10.10')
        self.assertEqual(host, 'Primary')

    def test_02_not_allowed_sender(self):
        self.assertRaises(MessageFromNotAuthorizedHost, self.manager.check_sender, '10.10.10.11')

    def test_03_manage_multiple_messages(self):
        self.loop.run_until_complete(
            utils.run_wait_close_multiple(self.manager.manage_message, self.manager, '10.10.10.10', self.msgs))
        expected_file = os.path.join(self.base_home, 'Encoded', 'Primary_TCAP_MAP.TCAPMAPMULTI')
        self.assertBinaryFileContentsEqual(expected_file, b"I\x00\x00\x00bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0\xad\x00\x00\x00e\x81\xaaH\x04\x84\x00\x01\xffI\x04\xa5\x05\x00\x01k*((\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x1da\x1b\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x0e\x03\xa2\x03\x02\x01\x00\xa3\x05\xa1\x03\x02\x01\x00l\x80\xa2l\x02\x01\x010g\x02\x018\xa3\x80\xa1\x800Z\x04\x10K\x9da\x91\x10u6e\x8c\xfeY\x88\x0c\xd2\xac'\x04\x10K\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8\x04\x10\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x04\x10C\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x8c\x04\x10\xa2U\x1a\x05\x8c\xdb\x00\x00K\x8dy\xf7\xca\xffP\x12\x00\x00\x00\x00\x00\x00\x18\x00\x00\x00e\x16H\x04\xa5\x05\x00\x01I\x04\x84\x00\x01\xffl\x08\xa1\x06\x02\x01\x02\x02\x018>\x00\x00\x00d<I\x04W\x18\x00\x00k*((\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x1da\x1b\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x05\x03\xa2\x03\x02\x01\x00\xa3\x05\xa1\x03\x02\x01\x00l\x08\xa3\x06\x02\x01\x01\x02\x01\x0b")
        msgs = self.interface.from_file_multi(self.sender, expected_file)
        self.assertSequenceEqual(self.multiple_encoded_hex, [binascii.hexlify(msg.encoded) for msg in msgs])
        expected_file = os.path.join(self.base_home, 'Decoded', 'Primary_TCAP_MAP.txt')
        self.assertFileContentsEqual(expected_file,
                                     '(\'begin\',\n {\'components\': [(\'basicROS\',\n                  (\'invoke\',\n                   {\'argument\': (\'RoutingInfoForSM-Arg\',\n                                 {\'msisdn\': b\'\\x91\\x14\\x97Bu3\\xf3\',\n                                  \'serviceCentreAddress\': b\'\\x91\\x14\\x97y\'\n                                                          b\'y\\x08\\xf0\',\n                                  \'sm-RP-PRI\': False}),\n                    \'invokeId\': (\'present\', -1),\n                    \'opcode\': (\'local\', 45)}))],\n  \'dialoguePortion\': {\'direct-reference\': (0, 0, 17, 773, 1, 1, 1),\n                      \'encoding\': (\'single-ASN1-type\',\n                                   (\'DialoguePDU\',\n                                    (\'dialogueRequest\',\n                                     {\'application-context-name\': (0,\n                                                                   4,\n                                                                   0,\n                                                                   0,\n                                                                   1,\n                                                                   0,\n                                                                   20,\n                                                                   2),\n                                      \'protocol-version\': (1, 1)})))},\n  \'otid\': b\'\\x00\\x00\\x00\\x01\'})\n\n(\'continue\',\n {\'components\': [(\'basicROS\',\n                  (\'returnResult\',\n                   {\'invokeId\': (\'present\', 1),\n                    \'result\': {\'opcode\': (\'local\', 56),\n                               \'result\': (\'SendAuthenticationInfoRes\',\n                                          {\'authenticationSetList\': (\'quintupletList\',\n                                                                     [{\'autn\': b\'\\xa2U\\x1a\\x05\'\n                                                                               b\'\\x8c\\xdb\\x00\\x00\'\n                                                                               b\'K\\x8dy\\xf7\'\n                                                                               b\'\\xca\\xffP\\x12\',\n                                                                       \'ck\': b\'\\x8cC\\xa2T\'\n                                                                             b\' P\\x12\\x04\'\n                                                                             b\'g\\xf33\\xc0\'\n                                                                             b\'\\x0fB\\xd8K\',\n                                                                       \'ik\': b\'C\\xa2T \'\n                                                                             b\'P\\x12\\x04g\'\n                                                                             b\'\\xf33\\xc0\\x0f\'\n                                                                             b\'B\\xd8K\\x8c\',\n                                                                       \'rand\': b\'K\\x9da\\x91\'\n                                                                               b\'\\x10u6e\'\n                                                                               b\'\\x8c\\xfeY\\x88\'\n                                                                               b"\\x0c\\xd2\\xac\'",\n                                                                       \'xres\': b\'K\\x8cC\\xa2\'\n                                                                               b\'T P\\x12\'\n                                                                               b\'\\x04g\\xf33\'\n                                                                               b\'\\xc0\\x0fB\\xd8\'}])})}}))],\n  \'dialoguePortion\': {\'direct-reference\': (0, 0, 17, 773, 1, 1, 1),\n                      \'encoding\': (\'single-ASN1-type\',\n                                   (\'DialoguePDU\',\n                                    (\'dialogueResponse\',\n                                     {\'application-context-name\': (0,\n                                                                   4,\n                                                                   0,\n                                                                   0,\n                                                                   1,\n                                                                   0,\n                                                                   14,\n                                                                   3),\n                                      \'protocol-version\': (1, 1),\n                                      \'result\': 0,\n                                      \'result-source-diagnostic\': (\'dialogue-service-user\',\n                                                                   0)})))},\n  \'dtid\': b\'\\xa5\\x05\\x00\\x01\',\n  \'otid\': b\'\\x84\\x00\\x01\\xff\'})\n\n(\'continue\',\n {\'components\': [(\'basicROS\',\n                  (\'invoke\',\n                   {\'invokeId\': (\'present\', 2), \'opcode\': (\'local\', 56)}))],\n  \'dtid\': b\'\\x84\\x00\\x01\\xff\',\n  \'otid\': b\'\\xa5\\x05\\x00\\x01\'})\n\n(\'end\',\n {\'components\': [(\'basicROS\',\n                  (\'returnError\',\n                   {\'errcode\': (\'local\', 11), \'invokeId\': (\'present\', 1)}))],\n  \'dialoguePortion\': {\'direct-reference\': (0, 0, 17, 773, 1, 1, 1),\n                      \'encoding\': (\'single-ASN1-type\',\n                                   (\'DialoguePDU\',\n                                    (\'dialogueResponse\',\n                                     {\'application-context-name\': (0,\n                                                                   4,\n                                                                   0,\n                                                                   0,\n                                                                   1,\n                                                                   0,\n                                                                   5,\n                                                                   3),\n                                      \'protocol-version\': (1, 1),\n                                      \'result\': 0,\n                                      \'result-source-diagnostic\': (\'dialogue-service-user\',\n                                                                   0)})))},\n  \'dtid\': b\'W\\x18\\x00\\x00\'})\n\n')
        expected_file = os.path.join(self.base_home, 'Prettified', 'Primary_TCAP_MAP.txt')
        self.assertFileContentsEqual(expected_file,
                                     """Event_type: begin
Otid: 00000001
Direct-reference: 0.0.17.773.1.1.1

Event_type: continue
Otid: 840001ff
Direct-reference: 0.0.17.773.1.1.1

Event_type: continue
Otid: a5050001
Direct-reference: 

Event_type: end
Otid: 00000000
Direct-reference: 0.0.17.773.1.1.1

"""
                                     )
        expected_file = os.path.join(self.base_home, 'Summaries', "Summary_%s.csv" % utils.current_date())
        self.assertPathExists(expected_file)
        with open(expected_file, 'r') as f:
            for i, l in enumerate(f):
                pass
        self.assertEqual(i + 1, 4)
