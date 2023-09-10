# -*- coding: utf-8 -*-
from logging.handlers import RotatingFileHandler
from pathlib import Path
import logging

LOG_DIR = Path(__file__).parent
LOG_FILE = LOG_DIR.joinpath('logfile.log')
LOG_FORMAT = '%(asctime)s :: %(levelname)-8s :: %(name)s :: %(message)s'


def get_logger(name: str) -> logging.Logger:
    """ Create a logger """
    formatter = logging.Formatter(fmt=LOG_FORMAT)

    # Create a custom logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # INFO and above go to console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # DEBUG and above go to file, file rotates every 1MB
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1e6, backupCount=1, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
