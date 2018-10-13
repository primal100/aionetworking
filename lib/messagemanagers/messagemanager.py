from .base import BaseMessageManager


class MessageManager(BaseMessageManager):

    async def done(self):
        return True

    def do_actions(self, msg):
        for action in self.actions:
            action.do(msg)
        for action in self.print_actions:
            action.print(msg)

    async def decode_run(self, host, encoded, timestamp):
        msg = self.message_cls(host, encoded, self.interface_config, timestamp=timestamp)
        self.do_actions(msg)
