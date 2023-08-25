"""Classes for adding joins to sqlalchemy queries."""

import importlib
from typing import Any

from alchemical_storage.visitor import StatementVisitor, T


class JoinVisitor(StatementVisitor):
    def __init__(self, joins: dict[tuple[str, ...], str | tuple[Any, ...]], import_from: str):
        self.__module = importlib.import_module(import_from)
        self.joins = {}
        for attrs, join in joins.items():
            if isinstance(join, str):
                join = [join]
            get_by = None
            for child in join[0].split('.'):
                if not get_by:
                    get_by = getattr(self.__module, child)
                else:
                    get_by = getattr(get_by, child)
            self.joins.update({attrs: (get_by, *join[1:])})

    def visit_statement(self, statement, params) -> T:
        for attrs, join in self.joins.items():
            if set(params.keys()).intersection(attrs):
                statement = statement.join(*join)
        return statement  # type: ignore
