from typing import Generic, TypeVar, Type, Optional, Sequence, Dict, Any, List
from uuid import UUID
from sqlalchemy import select, and_, or_, desc, asc, func
from sqlalchemy.orm import Session
from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository providing generic CRUD functionality with reusable filtering, sorting, and counting."""
    
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get(self, id: UUID) -> Optional[ModelType]:
        return self.db.get(self.model, id)

    def delete(self, id: UUID) -> bool:
        obj = self.get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
            return True
        return False

    def _build_conditions(
        self,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None,
        search_fields: Optional[List[str]] = None,
    ) -> List[Any]:
        """Helper to build query conditions based on filters and search parameters."""
        conditions = []

        # 1. Apply exact match and operator-based filters
        if filters:
            for key, value in filters.items():
                if value is None:
                    continue

                if "__" in key:
                    field_name, op = key.split("__", 1)
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        if op == "like":
                            conditions.append(field.like(value))
                        elif op == "ilike":
                            conditions.append(field.ilike(value))
                        elif op == "gt":
                            conditions.append(field > value)
                        elif op == "gte":
                            conditions.append(field >= value)
                        elif op == "lt":
                            conditions.append(field < value)
                        elif op == "lte":
                            conditions.append(field <= value)
                        elif op == "in":
                            conditions.append(field.in_(value))
                        elif op == "neq":
                            conditions.append(field != value)
                else:
                    if hasattr(self.model, key):
                        conditions.append(getattr(self.model, key) == value)

        # 2. Apply search queries (across multiple fields joined by OR)
        if search and search_fields:
            search_conditions = []
            for field_name in search_fields:
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    search_conditions.append(field.ilike(f"%{search}%"))
            if search_conditions:
                conditions.append(or_(*search_conditions))

        return conditions

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None,
        search_fields: Optional[List[str]] = None,
        sort_by: Optional[str] = None,
    ) -> Sequence[ModelType]:
        """
        Generic listing with support for:
        - Exact matches (via filters keys)
        - Partial matches and operators (via key__operator suffixes)
        - Text search (across multiple fields via search_fields)
        - Sorting (e.g. 'created_at' or '-created_at')
        """
        statement = select(self.model)
        conditions = self._build_conditions(filters, search, search_fields)

        if conditions:
            statement = statement.where(and_(*conditions))

        # Apply sorting
        if sort_by:
            is_desc = sort_by.startswith("-")
            field_name = sort_by[1:] if is_desc else sort_by
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                statement = statement.order_by(desc(field) if is_desc else asc(field))

        # Pagination
        statement = statement.offset(skip).limit(limit)
        return self.db.scalars(statement).all()

    def count(
        self,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None,
        search_fields: Optional[List[str]] = None,
    ) -> int:
        """Return the count of items matching the filters and search criteria."""
        statement = select(func.count()).select_from(self.model)
        conditions = self._build_conditions(filters, search, search_fields)

        if conditions:
            statement = statement.where(and_(*conditions))

        return self.db.scalar(statement) or 0
