import inspect
import logging
import os
import sys
import traceback


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    format = "%(asctime)s | %(levelname)s | %(message)s"
    Formats = {
        logging.DEBUG: ''.join([grey, format]),
        logging.INFO: ''.join([yellow, format]),
        logging.ERROR: ''.join([red, format])
    }

    def format(self, record):
        log_fmt = self.Formats.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class Logger:
    def __init__(self, name=None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.log_path = None
        self.stream_handler = None

    def setup_logger_file(self, path, device=''):
        """ Sets up log instances and creates the log handlers for
        redirection of logs to the created path/folder.

        Args:
            path: log path
            device: name of the device.
        """
        self.log_path = path
        log_format = "%(asctime)s | %(levelname)s | %(message)s"
        formatter = logging.Formatter(log_format)
        if device != '':
            device = '_'.join([device, ''])
        debug_path = '/'.join([self.log_path, ''.join([device, 'debug.log'])])
        debug_handler = logging.FileHandler(debug_path)
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(formatter)
        self.logger.addHandler(debug_handler)

        error_path = '/'.join([self.log_path, ''.join([device, 'error.log'])])
        error_handler = logging.FileHandler(error_path)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)

        info_path = '/'.join([self.log_path, ''.join([device, 'info.log'])])
        info_handler = logging.FileHandler(info_path)
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(formatter)
        self.logger.addHandler(info_handler)

        if not self.stream_handler:
            self.stream_handler = logging.StreamHandler(sys.stdout)
            self.stream_handler.setLevel(logging.DEBUG)
            self.stream_handler.setFormatter(CustomFormatter())
            self.logger.addHandler(self.stream_handler)

    def cleanup_logger(self, name):
        """ Deletes all the handlers created in a session."""
        self.logger = logging.getLogger(name)
        while self.logger.handlers:
            if 'StreamHandler' in str(self.logger.handlers[0]):
                self.stream_handler = None
            self.logger.removeHandler(self.logger.handlers[0])

    def get_logger(self, name):
        """Sets logging instance based on name."""
        self.logger = logging.getLogger(name)

    def function_property(self):
        """Returns function name and file name of caller function."""
        function = inspect.currentframe().f_back.f_back.f_code
        function_name = function.co_name
        filename = os.path.splitext(function.co_filename.split('/')[-1])[0]
        return function_name, filename

    def info(self, message):
        """Logs a message with log level INFO(Numeric representation: 20)"""
        function_name, filename = self.function_property()
        self.logger.info("%s | %s | %s" % (filename, function_name, message))

    def debug(self, message):
        """Logs a message with log level DEBUG(Numeric representation: 10)"""
        function_name, filename = self.function_property()
        self.logger.debug("%s | %s | %s" % (filename, function_name, message))

    def error(self, message):
        """Logs a message with log level ERROR(Numeric representation: 40)"""
        function_name, filename = self.function_property()
        self.logger.error("%s | %s | %s" % (filename, function_name, message))
        self.logger.error(traceback.format_exc())
