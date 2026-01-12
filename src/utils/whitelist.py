from typing import Literal

from redis.asyncio import Redis

from config import get_config

cfg = get_config()

redis = Redis(host=cfg.REDIS_HOST, port=cfg.REDIS_PORT, db=0, decode_responses=True)


class TokenWhiteList:
    async def add_jti_to_whitelist(
        self, id: str, jti: str, entity: Literal["user", "company"]
    ) -> None:
        if entity == "user":
            string = f"whitelist:users:{id}"
        elif entity == "company":
            string = f"whitelist:companies:{id}"
        else:
            raise ValueError("Entity should be ether user or company")
        await redis.sadd(string, jti)

    async def check_jti_in_whitelist(
        self, id: str, jti: str, entity: Literal["user", "company"]
    ) -> bool:
        if entity == "user":
            string = f"whitelist:users:{id}"
        elif entity == "company":
            string = f"whitelist:companies:{id}"
        else:
            raise ValueError("Entity should be ether user or company")
        exists = await redis.sismember(string, jti)
        return exists

    async def delete_one_jti_from_whitelist(
        self, id: str, jti, entity: Literal["user", "company"]
    ):
        if entity == "user":
            string = f"whitelist:users:{id}"
        elif entity == "company":
            string = f"whitelist:companies:{id}"
        else:
            raise ValueError("Entity should be ether user or company")
        await redis.srem(string, jti)

    async def flush_all_jti_from_whitelist(
        self, id: str, entity: Literal["user", "company"]
    ) -> None:
        if entity == "user":
            string = f"whitelist:users:{id}"
        elif entity == "company":
            string = f"whitelist:companies:{id}"
        else:
            raise ValueError("Entity should be ether user or company")
        await redis.unlink(string)
