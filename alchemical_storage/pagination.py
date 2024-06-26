"""Module containing pagination statement visitors."""

from typing import Any

from alchemical_storage.visitor import StatementVisitor, T


class PaginationMap(StatementVisitor):
    """Class for adding pagination to sqlalchemy queries.

    Args:
        param_name (str): The name of the parameter containing the pagination
            object.
        page_size_attr (str): The attribute name for the page size within the
            pagination object.
        first_item_attr (str): The attribute name for the first item within the
            pagination object.

    """

    def __init__(
        self, param_name: str, page_size_attr: str, first_item_attr: str
    ) -> None:
        self._param_name = param_name
        self._page_size_attr = page_size_attr
        self._first_item_attr = first_item_attr

    def visit_statement(self, statement: T, params: dict[str, Any]) -> T:
        """Apply pagination to an sqlalchemy query. Ignored if ``param_name`` key is not
        in ``params``.

        Args:
            statement (T): The sqlalchemy statement to apply pagination to
            params (dict[str, Any]): The filters to apply

        Returns:
            T: The paginated sqlalchemy statement

        """
        if self._param_name not in params:
            return statement
        page_params = params[self._param_name]
        return statement.limit(getattr(page_params, self._page_size_attr)).offset(
            getattr(page_params, self._first_item_attr)
        )
