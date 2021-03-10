import logging


class LoggingMixin(object):
    @property
    def logger(self):
        name = '.'.join([
            self.__module__,
            self.__class__.__name__
        ])
        return logging.getLogger(name)


class ConfigMixin(object):
    @property
    def config(self):
        """
        Returns the bots config.py file
        """
        return __import__('config')
