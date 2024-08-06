import logging
from logging import Logger
from settings import FLASK_ENV


def get_logger(name):
    level = logging.DEBUG if FLASK_ENV == "development" else logging.INFO
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


logger = get_logger("app")
