import os
import zlib
import redis
import pickle

from core import log
from typing import Any, Optional

class RedisService:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=False)
            self.client.ping()
            log.info(f"Đã kết nối Redis tại {self.redis_url}")
        except Exception as e:
            log.error(f"Lỗi kết nối Redis: {e}")
            self.client = None
    
    def set_object(self, key: str, obj: Any, ttl: int = 86400):
        if not self.client: 
            return
    
        try:
            serialized = pickle.dumps(obj)
            compressed = zlib.compress(serialized)
            self.client.setex(key, ttl, compressed)
        except Exception as e:
            log.error(f"Redis Set Error: {e}")
    
    def get_object(self, key: str) -> Optional[Any]:
        if not self.client: 
            return None
    
        try:
            compressed = self.client.get(key)
            if compressed is None:
                return None
            
            serialized = zlib.decompress(compressed)
            obj = pickle.loads(serialized)
            return obj
        except Exception as e:
            log.error(f"Redis Get Error: {e}")
            return None

redis_service = RedisService()
        