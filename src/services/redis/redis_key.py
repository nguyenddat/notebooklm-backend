class RedisKeys:
    PREFIX = "notebook"
    
    @classmethod
    def flat_sections(cls, file_hash: str) -> str:
        return f"{cls.PREFIX}:docling:flat:{file_hash}"

    @classmethod
    def task_status(cls, task_id: str) -> str:
        return f"{cls.PREFIX}:task:{task_id}"
    
    @classmethod
    def image_caption(cls, image_hash: str) -> str:
        return f"{cls.PREFIX}:image:caption:{image_hash}"