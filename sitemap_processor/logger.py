import os
import logging
from logging import Logger


def get_logger(name, level=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def set_prefix(logger: Logger, prefix):
    formatter = logging.Formatter(
        f'%(asctime)s - {prefix} - %(levelname)s - %(message)s')
    for handler in logger.handlers:
        handler.setFormatter(formatter)

    return logger


ENV = os.environ.get('ENV', 'development')
level = logging.DEBUG if ENV == "development" else logging.INFO
logger = get_logger('sitemap_processor', level)
