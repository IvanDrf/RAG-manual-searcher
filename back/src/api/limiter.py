from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.config import CONFIG

limiter = Limiter(key_func=get_remote_address, storage_uri=f"redis://{CONFIG.redis_host}:{CONFIG.redis_port}")
