import asyncio
from collections.abc import MutableMapping

import bcrypt

from config import get_config
from utils.logger import logger

cfg = get_config()


async def hash_password(password_text: str) -> str:
    if cfg.DEBUG:
        bytes_n = password_text.encode()
        logger.debug(f"Number of bytes in password: {bytes_n}")
    loop = asyncio.get_event_loop()
    hashed = await loop.run_in_executor(
        None, bcrypt.hashpw, password_text.encode(), bcrypt.gensalt()
    )
    return hashed.decode("utf-8")


async def verify_password(password_text: str, password_hash: str) -> bool:
    loop = asyncio.get_event_loop()
    verified = await loop.run_in_executor(
        None, bcrypt.checkpw, password_text.encode(), password_hash.encode()
    )
    return verified


def flatten(dictionary, parent_key="", separator="."):
    items = []
    for key, value in dictionary.items():
        new_key = parent_key + separator + key if parent_key else key
        if isinstance(value, MutableMapping):
            items.extend(flatten(value, new_key, separator=separator).items())
        else:
            items.append((new_key, value))
    return dict(items)
