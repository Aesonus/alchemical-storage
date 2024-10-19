"""Classes to add ``where`` and ``order_by`` clauses to ``sqlalchemy.Select`` instances
in the ``DatabaseIndex.get`` method."""

import functools
import operator
from types import ModuleType
from typing import Any, Callable, Generator

from sqlalchemy.sql.expression import desc

from alchemical_storage import get_module
from alchemical_storage.filter.exc import NullFilterException, OrderByException
from alchemical_storage.visitor import StatementVisitor, T

# pylint: disable=too-few-public-methods


class FilterMap(StatementVisitor):
    """Maps :meth:`FilterMap.visit_statement<.FilterMap.visit_statement>` ``params``
    argument dict keys to ``sqlalchemy.Select.where`` calls.

    Arguments:
        filters: A dictionary of filters
        import_from: The module to import Model classes from

    Example:
        .. code-block:: python

            filter_visitor = FilterMap({
                "game_type": 'Game.type',
                "starting_at": ('Game.played_on', operator.ge,),
                "ending_at": ('Game.played_on', operator.le,),
            }, 'your_models_module.models')

    See Also:
        :ref:`Using Filters > FilterMap <UsingFilterMap>`

    """

    filters: dict[str, Callable]

    def __init__(self, filters: dict[str, Any], import_from: str | ModuleType) -> None:
        self.__module = get_module(import_from)
        self.filters = {}
        for filter_, exprs in filters.items():
            if isinstance(exprs, tuple):
                attr, op_ = exprs
            else:
                attr = exprs
                op_ = operator.eq
            get_by = None
            for child in attr.split("."):
                if not get_by:
                    get_by = getattr(self.__module, child)
                else:
                    get_by = getattr(get_by, child)
            self.filters[filter_] = functools.partial(op_, get_by)

    def visit_statement(self, statement: T, params: dict[str, Any]):
        """Apply filters to an ``sqlalchemy.Select`` instance. Each key in ``params``
        corresponds to a filter configured in the constructor. If the ``params`` key is
        not configured, it is ignored.

        Arguments:
            statement: The ``sqlalchemy.Select`` instance to apply ``where`` filters to
            params: The filters and their parameters to apply

        Returns:
            The new ``sqlalchemy.Select`` instance with the filters applied

        """
        return statement.where(*self._generate_whereclauses(params))

    def _generate_whereclauses(
        self, given_filters: dict[str, Any]
    ) -> Generator[Any, None, None]:
        for attr, filtered_by in given_filters.items():
            if attr in self.filters:
                yield self.filters[attr](filtered_by)


class OrderByMap(StatementVisitor):
    """Maps the value of the
    :meth:`FilterMap.visit_statement<.FilterMap.visit_statement>` ``params`` argument
    ``order_by`` key to ``sqlalchemy.Select.order_by`` calls.

    Arguments:
        order_by_attributes: A dictionary of order_by attributes, where
            the key is the attribute name and the value is the column or label to order
            by.
        import_from: The module to import Model classes from

    Example:
        .. code-block:: python

            order_by_visitor = OrderByMap({
                "game_type": 'Game.type',
                "player_on": 'Game.played_on',
            }, 'your_models_module.models')

    See Also:
        :ref:`Sorting Results <UsingOrderByMap>`

    """

    order_by_attributes: dict[str, Any]

    def __init__(
        self, order_by_attributes: dict[str, Any], import_from: str | ModuleType
    ) -> None:
        module = get_module(import_from)
        self.order_by_attributes = {}
        for attr, column in order_by_attributes.items():
            if "." in column:
                model, model_attr = column.split(".")
                order_by = getattr(getattr(module, model), model_attr)
            else:
                order_by = column

            self.order_by_attributes[attr] = order_by

    def visit_statement(self, statement: T, params: dict[str, Any]):
        """Apply order_by criteria to a ``sqlalchemy.Select`` instance. Ignored if
        ``order_by`` key is not in ``params`` keys.

        Arguments:
            statement: The ``sqlalchemy.Select`` instance to apply ``order_by``
                criteria to
            params: The order_by criteria to apply

        Returns:
            The new ``sqlalchemy.Select`` instance with the order_by criteria applied

        Raises:
            OrderByException: If an unknown order_by value is encountered

        """
        if "order_by" not in params:
            return statement
        return statement.order_by(*self._generate_order_by(params["order_by"]))

    def _generate_order_by(self, order_by: str):
        for attr in order_by.split(","):
            if attr.startswith("-"):
                order = "desc"
                attr = attr[1:]
            else:
                order = "asc"
            if attr in self.order_by_attributes:
                if order == "desc":
                    yield desc(self.order_by_attributes[attr])
                else:
                    yield self.order_by_attributes[attr]
            else:
                raise OrderByException(f"Unknown order_by attribute: {attr}")


class NullFilterMap(StatementVisitor):
    """Maps :meth:`FilterMap.visit_statement<.FilterMap.visit_statement>` ``params``
    argument dict keys to ``sqlalchemy.Select.where`` calls specifically for ``NULL`` or
    ``NOT NULL`` filters.

    Arguments:
        filters: A dictionary of filters
        import_from: The module to import Model classes from

    Keyword Arguments:
        null_identifiers: The identifiers for null and not null.
            Defaults to ``("null", "not-null")``.

    Example:
        .. code-block:: python

            null_filter_visitor = NullFilterMap({
                "deleted_at": 'Game.deleted_at',
            }, 'your_models_module.models')

    See Also:
        :ref:`Usage Guide for NullFilterMap <UsingNullFilterMap>`

    """

    filters: dict[str, Any]
    null_identifiers: tuple[str, str]

    def __init__(
        self,
        filters: dict[str, Any],
        import_from: str | ModuleType,
        null_identifiers: tuple[str, str] = ("null", "not-null"),
    ) -> None:
        self.__module = get_module(import_from)
        self.filters = {}
        self.null_identifiers = null_identifiers
        for filter_, attr in filters.items():
            get_by = None
            for child in attr.split("."):
                if not get_by:
                    get_by = getattr(self.__module, child)
                else:
                    get_by = getattr(get_by, child)
            self.filters[filter_] = get_by

    def visit_statement(self, statement: T, params: dict[str, Any]) -> T:
        """Apply filters to an ``sqlalchemy.Select`` instance. Each key in ``params``
        corresponds to a filter configured in the constructor. If the ``params`` key is
        not configured, it is ignored.

        Arguments:
            statement: The ``sqlalchemy.Select`` instance to apply ``where`` filters to
            params: The filters and their parameters to apply

        Returns:
            The new ``sqlalchemy.Select`` instance with the filters applied

        Raises:
            NullFilterException: If an unknown filter value is encountered

        """
        return statement.where(*self._generate_where_clauses(params))

    def _generate_where_clauses(self, given_filters: dict[str, Any]):
        null, not_null = self.null_identifiers
        for attr, filtered_by in given_filters.items():
            if attr in self.filters:
                if filtered_by == null:
                    yield self.filters[attr].is_(None)
                elif filtered_by == not_null:
                    yield self.filters[attr].isnot(None)
                else:
                    raise NullFilterException(
                        f"Unknown filter value: '{filtered_by}' for `{attr}`"
                    )
