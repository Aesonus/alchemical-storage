"""Contains the visitor interface for sqlalchemy statements."""

import abc
from typing import Any, TypeVar

import sqlalchemy as sql

T = TypeVar("T", bound=sql.Select)


class StatementVisitor(abc.ABC):
    """Visitor class for sqlalchemy statements."""

    @abc.abstractmethod
    def visit_statement(self, statement: T, params: dict[str, Any]) -> T:
        """Visit a statement.

        Args:
            statement: The statement to visit
            params: The parameters passed by the
                :class:`alchemical_storage.storage.DatabaseStorage` when this method is
                called

        Returns:
            T: The visited statement

        """
