"""Classes for adding joins to sqlalchemy queries."""

import importlib
from typing import Any

from alchemical_storage.visitor import StatementVisitor, T

JoinExpression = str | tuple[Any, ...]


class JoinMap(StatementVisitor):
    """
    Class for adding joins to sqlalchemy queries.

    Args:
        import_from (str): The module to import the models/entities from.
        param_names (tuple[str, ...]): The names of the parameters that will trigger the join.
            Any of these parameters being in the ``params`` dict passed to ``visit_statement``
            will trigger the join.
        *joins (str | tuple[Any, ...]): The joins to add to the query.

    Example:
        ::

            from alchemical_storage.join import JoinMap
            from tests.models import Model, RelatedToModel

            join_map = JoinMap(
                'tests.models', ('join_param', ), ('RelatedToModel', )
            )

    """

    joins: tuple[tuple[Any, ...], ...]

    def __init__(
        self,
        import_from: str,
        param_names: tuple[str, ...],
        *joins: JoinExpression,
    ):
        self.__module = importlib.import_module(import_from)
        self.param_names = param_names
        _joins = []
        for join in joins:
            _joins.append(self._get_join(join))
        self.joins = tuple(_joins)

    def _import_entity(self, entity: str) -> Any:
        get_by = None
        for child in entity.split("."):
            if not get_by:
                get_by = getattr(self.__module, child)
            else:
                get_by = getattr(get_by, child)
        return get_by

    def _get_join(self, join: JoinExpression) -> tuple[Any, ...]:
        if isinstance(join, str):
            join = (join,)
        if isinstance(join[0], str):
            get_by = self._import_entity(join[0])
        else:
            get_by = join[0]
        processed_joins = []
        for join_part in join[1:]:
            if isinstance(join_part, str):
                join_part = self._import_entity(join_part)
            processed_joins.append(join_part)
        return (get_by, *processed_joins)

    def visit_statement(self, statement: T, params: dict[str, Any]) -> T:
        if set(params.keys()).intersection(self.param_names):
            for join in self.joins:
                statement = statement.join(*join)
        return statement
