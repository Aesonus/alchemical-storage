"""Write a visitor class that modifies an sqlalchemy statement"""

import abc
from typing import Any, TypeVar

import sqlalchemy as sql

T = TypeVar('T', sql.Select, sql.ColumnElement)


class StatementVisitor(abc.ABC):
    """Visitor class for sqlalchemy statements"""
    @abc.abstractmethod
    def visit_statement(self, statement: T,
                        params: dict[str, Any]
                        ) -> T:
        """Visit a statement"""
