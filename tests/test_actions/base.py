import binascii
import datetime
import shutil
from pathlib import Path

from lib.basetestcase import BaseTestCase
from lib.protocols.contrib.TCAP_MAP import TCAP_MAP_ASNProtocol
from lib.actions.base import BaseAction


class BaseTCAPMAPActionTestCase(BaseTestCase):
    encoded_hex = b'62474804000000016b1e281c060700118605010101a011600f80020780a1090607040000010014026c1fa11d0201ff02012d30158007911497427533f38101008207911497797908f0'
    multiple_encoded_hex = (
        b'62474804000000016b1e281c060700118605010101a011600f80020780a1090607040000010014026c1fa11d0201ff02012d30158007911497427533f38101008207911497797908f0',
        b'6581aa4804840001ff4904a50500016b2a2828060700118605010101a01d611b80020780a109060704000001000e03a203020100a305a1030201006c80a26c0201013067020138a380a180305a04104b9d6191107536658cfe59880cd2ac2704104b8c43a2542050120467f333c00f42d804108c43a2542050120467f333c00f42d84b041043a2542050120467f333c00f42d84b8c0410a2551a058cdb00004b8d79f7caff5012000000000000',
        b'65164804a50500014904840001ff6c08a106020102020138',
        b'643c4904571800006b2a2828060700118605010101a01d611b80020780a109060704000001000503a203020100a305a1030201006c08a30602010102010b'
    )
    protocol = TCAP_MAP_ASNProtocol
    action_cls = BaseAction
    sender = '10.10.10.10'

    def setUp(self):
        try:
            shutil.rmtree(Path(self.base_data_dir, BaseAction.default_data_dir))
        except OSError:
            pass
        self.action = self.action_cls()
        self.print_action = self.action_cls(storage=False)
        timestamp = datetime.datetime(2018, 1, 1, 1, 1)
        self.msg = self.protocol.from_buffer(self.sender, binascii.unhexlify(self.encoded_hex), timestamp=timestamp)[0]
        self.msgs = [self.protocol.from_buffer(self.sender, binascii.unhexlify(encoded_hex), timestamp=timestamp)[0] for encoded_hex in
                     self.multiple_encoded_hex]
