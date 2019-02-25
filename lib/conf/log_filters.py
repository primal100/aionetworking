import logging
import operator


class BaseFilter(logging.Filter):
    configurable = {
        'class': str,
        'loggers': tuple,
    }

    @classmethod
    def with_config(cls, config, section_name, *args, **kwargs):
        return cls(*args, **kwargs)

    @classmethod
    def from_config(cls, section_name, cp=None, *args, **kwargs):
        from lib import settings, definitions
        full_section_name = "filter_%s" % section_name
        cp = cp or settings.CONFIG
        config = cp.section_as_dict(full_section_name, **cls.configurable)
        config.update(kwargs)
        cls_name = config.pop('class')
        actual_cls = definitions.LOG_FILTERS[cls_name]
        return actual_cls.with_config(cp, full_section_name, *args, **config)

    def __init__(self, loggers, *args, **kwargs):
        super(BaseFilter, self).__init__(*args, **kwargs)
        for name in loggers:
            logger = logging.getLogger(name)
            logger.addFilter(self)


class SenderFilter(BaseFilter):
    configurable = BaseFilter.configurable
    configurable.update({'senders': tuple})

    def __init__(self, senders, *args, **kwargs):
        self.senders = senders
        super(SenderFilter, self).__init__(*args, **kwargs)

    def filter(self, record):
        sender = getattr(record, 'sender', None)
        if not sender:
            msg_obj = getattr(record, 'msg_obj', None)
            if msg_obj:
                sender = msg_obj.sender
                return sender in self.senders
            return True
        return sender in self.senders


class MessageFilter(BaseFilter):
    configurable = BaseFilter.configurable
    configurable.update({'attr': str, 'operator': str, 'valuetype': str})

    @classmethod
    def with_config(cls, config, section_name, *args, valuetype='str', **kwargs):
        data_type = getattr(__builtins__, valuetype)
        kwargs['value'] = config.get(section_name, 'value', data_type)
        return cls(*args, valuetype=valuetype, **kwargs)

    def __init__(self, attr, value, op='eq', valuetype='str', case_sensitive=True, *args, **kwargs):
        self.attr = attr
        if valuetype == str:
            case_sensitive = True
        self.value = value
        self.operator = getattr(operator, op)
        self.case_sensitive = case_sensitive
        super(MessageFilter, self).__init__(*args, **kwargs)

    def filter(self, record):
        msg_obj = getattr(record, 'msg_obj', None)
        if msg_obj:
            value = getattr(msg_obj, self.attr, None)
            data_type = type(value)
            if self.case_sensitive or not data_type == str:
                return self.operator(value, data_type(self.value))
            return self.operator(value.lower, self.value.lower())
        return True
