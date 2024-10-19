"""Classes to get indexes of resources from a database."""

from typing import Any, Callable, Generic, Optional, TypeVar

import sqlalchemy as sql
from sqlalchemy import orm
from typing_extensions import deprecated

from alchemical_storage.visitor import StatementVisitor

EntityType = TypeVar("EntityType", bound=Any)  # pylint: disable=invalid-name


class DatabaseIndex(Generic[EntityType]):
    """Gets or counts resources from a database.

    Arguments:
        session: The database session.
        entity: The entity type. Usually a SQLAlchemy model or tuple of them.
        count_key: The callable that receives the entity type and returns the column
            to be used in the ``sqlalchemy.count`` function.

    Keyword Arguments:
        statement_visitors: List of statement visitors. Defaults to an empty list.

    """

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

    def get(self, **kwargs) -> list[EntityType] | list[sql.Row[EntityType]]:
        """Get a list (index) of resources from storage.

        Arguments:
            **kwargs: Parameters to pass to the statement visitors.

        Returns:
            List of models or rows if entity is a tuple.

        """
        if isinstance(self.entity, tuple):
            stmt = sql.select(*self.entity)
        else:
            stmt = sql.select(self.entity)
        for visitor in self._statement_visitors:
            stmt = visitor.visit_statement(stmt, kwargs)
        if isinstance(self.entity, tuple):
            return [*self.session.execute(stmt).unique().all()]
        return [*self.session.execute(stmt).unique().scalars().all()]

    @deprecated("Use count instead.")
    def count_index(self, **kwargs) -> int:
        """Count resources in storage.

        Deprecated. Use ``count`` instead.

        """
        return self.count(**kwargs)

    def count(self, **kwargs) -> int:
        """Count resources in storage.

        Arguments:
            **kwargs: Parameters to pass to the statement visitors.

        Returns:
            The count of resources in storage.

        """
        stmt = sql.select(sql.func.count(self._count_key(self.entity)))
        for visitor in self._statement_visitors:
            stmt = visitor.visit_statement(stmt, kwargs)
        return self.session.execute(stmt).unique().scalar_one()
