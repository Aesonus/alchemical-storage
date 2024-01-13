"""Index module."""

from typing import Any, Callable, Generic, Optional, TypeVar

import sqlalchemy as sql
from sqlalchemy import orm

from alchemical_storage.visitor import StatementVisitor

EntityType = TypeVar("EntityType", bound=Any)  # pylint: disable=invalid-name


class DatabaseIndex(Generic[EntityType]):
    """Database index."""

    def __init__(
        self,
        session: orm.Session,
        entity: EntityType,
        count_key: Callable[[EntityType], Any],
        statement_visitors: Optional[list[StatementVisitor]] = None,
    ):
        self.session = session
        self.entity = entity
        self._statement_visitors = statement_visitors or []
        self._count_key = count_key

    def get(self, page_params=None, **kwargs) -> list[Any]:
        """Get a list resources from storage."""
        if isinstance(self.entity, tuple):
            stmt = sql.select(*self.entity)
        else:
            stmt = sql.select(self.entity)
        for visitor in self._statement_visitors:
            stmt = visitor.visit_statement(stmt, kwargs)
        if page_params:
            stmt = stmt.limit(page_params.page_size).offset(page_params.first_item)
        if isinstance(self.entity, tuple):
            return [*self.session.execute(stmt).unique().all()]
        return [*self.session.execute(stmt).unique().scalars().all()]

    def count(self, **kwargs) -> int:
        """Count resources in storage."""
        # pylint: disable=not-callable

        stmt = sql.select(sql.func.count(self._count_key(self.entity)))
        for visitor in self._statement_visitors:
            stmt = visitor.visit_statement(stmt, kwargs)
        return self.session.execute(stmt).unique().scalar_one()
