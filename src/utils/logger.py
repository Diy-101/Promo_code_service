import logging

from config import get_config

cfg = get_config()
logger = logging.getLogger("uvicorn")

if cfg.DEBUG:
    logger.setLevel(logging.DEBUG)
