"""
Build upon the ``alchemical_storage.visitor`` module to create a classes that can be used to map
filters and order_by attributes to sqlalchemy statements.
"""

import functools
import importlib
import operator
from typing import Any, Callable, Generator

from sqlalchemy.sql.expression import desc

from alchemical_storage.filter.exc import OrderByException
from alchemical_storage.visitor import StatementVisitor, T

# pylint: disable=too-few-public-methods


class FilterMap(StatementVisitor):
    """
    Initialize the filter mapper

    Args:
        filters (dict[str, Any]): A dictionary of filters
        import_from (str): The module to import Model classes from

    Example:
        ::

            filter_visitor = FilterMap({
                "game_type": 'Game.type',
                "starting_at": ('Game.played_on', operator.ge,),
                "ending_at": ('Game.played_on', operator.le,),
            }, 'your_models_module.models')


    Note:
        + May use sqlalchemy's `sqlalchemy.sql.operators` for the operator.
        + The `your_models_module.models` is the module where the models are defined.
    """

    filters: dict[str, Callable]

    def __init__(self, filters: dict[str, Any], import_from: str) -> None:
        self.__module = importlib.import_module(import_from)
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
        """
        Apply filters to an sqlalchemy query. Each key in ``params`` corresponds to a filter
        in ``self.filters``. If the key is not in ``self.filters``, it is ignored.

        Args:
            statement (T): The sqlalchemy statement to apply filters to
            params (dict[str, Any]): The filters to apply

        Returns:
            T: The filtered sqlalchemy statement

        Note:
            Type "T" is a generic type that can be either a ``sqlalchemy.sql.Select`` or
            ``sqlalchemy.sql.ColumnElement``. This is because the visitor can be used
            on both select statements and column elements.
        """
        return statement.where(*self._generate_whereclauses(params))

    def _generate_whereclauses(
        self, given_filters: dict[str, Any]
    ) -> Generator[Any, None, None]:
        for attr, filtered_by in given_filters.items():
            if attr in self.filters:
                yield self.filters[attr](filtered_by)


class OrderByMap(StatementVisitor):
    """
    A mapper to convert order_by attributes to sqlalchemy order_by expressions

    Args:
        order_by_attributes (dict[str, Any]): A dictionary of order_by attributes, where
            the key is the attribute name and the value is the column or label to order by.
        import_from (str): The module to import Model classes from

    Example:
        ::

            order_by_visitor = OrderByMap({
                "game_type": 'Game.type',
                "player_on": 'Game.played_on',
            }, 'your_models_module.models')
    """

    order_by_attributes: dict[str, Any]

    def __init__(self, order_by_attributes: dict[str, Any], import_from: str) -> None:
        module = importlib.import_module(import_from)
        self.order_by_attributes = {}
        for attr, column in order_by_attributes.items():
            if "." in column:
                model, model_attr = column.split(".")
                order_by = getattr(getattr(module, model), model_attr)
            else:
                order_by = column

            self.order_by_attributes[attr] = order_by

    def visit_statement(self, statement, params: dict[str, Any]):
        """
        Apply order_by to an sqlalchemy query. Ignores order_by if not given in params.

        Args:
            statement (T): The sqlalchemy statement to apply order_by to
            params (dict[str, Any]): The filters to apply

        Returns:
            (T): The order_by sqlalchemy statement
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
