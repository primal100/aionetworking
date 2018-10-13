import asyncio
import atexit


def start(APP_NAME, single_message_manager, batch_message_manager, receivers, actions, interfaces, config):
    receiver_cls = receivers[config['receiver']['Type']]
    message_manager_cls = batch_message_manager if config['batch'] else single_message_manager
    interface_cls = interfaces[config['interface']]
    action_modules = [actions[a] for a in config['actions']['Types']]
    print_modules = [actions[a] for a in config['print']['Types']]
    loop = asyncio.get_event_loop()
    manager = message_manager_cls(APP_NAME, interface_cls, action_modules, print_modules, config['interface'], config['actions'],
                                  config['messagemanager'], loop=loop)
    receiver = receiver_cls(manager, config['receiver'], loop=loop)
    atexit.register(receiver.stop)
