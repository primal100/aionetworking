from .base import BaseMessageManager


class MessageManager(BaseMessageManager):

    async def done(self):
        return True

    def do_actions(self, msg):
        for action in self.actions:
            action.do(msg)
        for action in self.print_actions:
            action.print(msg)

    async def decode_run(self, sender, encoded, timestamp):
        msg = self.make_message(sender, encoded, timestamp)
        if not msg.filter():
            self.do_actions(msg)
