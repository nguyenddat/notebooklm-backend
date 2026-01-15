class RedisKeys:
    PREFIX = "notebook"
    
    @classmethod
    def doc_cache(cls, file_hash: str) -> str:
        return f"{cls.PREFIX}:docling:cache:{file_hash}"

    @classmethod
    def task_status(cls, task_id: str) -> str:
        return f"{cls.PREFIX}:task:{task_id}"