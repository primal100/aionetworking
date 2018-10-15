import asyncio
import atexit


def start(app_name, receivers, actions, interfaces, config):
    receiver_cls = receivers[config.receiver]
    message_manager_cls = config.message_manager
    interface_cls = interfaces[config.interface]
    loop = asyncio.get_event_loop()
    manager = message_manager_cls(app_name, interface_cls, actions, config, loop=loop)
    receiver = receiver_cls(manager, config, loop=loop)
    atexit.register(receiver.stop)
