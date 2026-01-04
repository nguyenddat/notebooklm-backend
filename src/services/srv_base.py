from typing import Type, TypeVar, Generic, List, Optional

from sqlalchemy import asc
from sqlalchemy.orm import Session

T = TypeVar("T")
class BaseService(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

    def add(self, obj: T, db: Session) -> T:
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def get_by_id(self, obj_id: int, db: Session) -> T | None:
        return db.query(self.model).filter(self.model.id == obj_id).first()

    def get_all_paginated(
        self,
        db: Session,
        limit: int = 20,
        last_id: Optional[int] = None,
    ) -> List[T]:
        query = db.query(self.model)

        if last_id is not None:
            query = query.filter(self.model.id > last_id)

        return (
            query
            .order_by(asc(self.model.id))
            .limit(limit)
            .all()
        )
    
    def update(self, obj_id: int, update_data: dict, db: Session) -> T | None:
        exists = self.get_by_id(obj_id, db)
        if not exists:
            return None

        for key, value in update_data.items():
            if hasattr(exists, key):
                setattr(exists, key, value)

        db.commit()
        db.refresh(exists)
        return exists

    def delete(self, obj_id: int, db: Session) -> T | None:
        exists = self.get_by_id(obj_id, db)
        if not exists:
            return None

        db.delete(exists)
        db.commit()
        return exists