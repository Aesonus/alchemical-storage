"""A filter mapper for storage queries"""

import functools
import importlib
import operator
from typing import Any, Callable, Generator

from sqlalchemy.sql.expression import desc

from alchemical_storage.filter.exc import OrderByException

# pylint: disable=too-few-public-methods


class FilterMap:
    """
    Usage
    ------
    ```
    self.filter_mapper = FilterMap({
            "opponent_type": 'Opponent.type',
            "starting_at": ('Game.played_on', operator.ge,),
            "ending_at": ('Game.played_on', operator.le,),
        }, 'your_models_module.models')
    ```
    + May also use sqlalchemy's `sqlalchemy.sql.operators` for the operator.
    + User-defined operator functions are also allowed.
    + The `your_models_module.models` is the module where the models are defined.
    """
    filters: dict[str, Callable]

    def __init__(self, filters: dict[str, Any], import_from: str) -> None:
        """
        Initialize the filter mapper

        Args:
            filters (dict[str, Any]): A dictionary of filters
            import_from (str): The module to import Model classes from
        """
        self.__module = importlib.import_module(import_from)
        self.filters = {}
        for filter_, exprs in filters.items():
            if isinstance(exprs, tuple):
                attr, op_ = exprs
            else:
                attr = exprs
                op_ = operator.eq
            get_by = None
            for child in attr.split('.'):
                if not get_by:
                    get_by = getattr(self.__module, child)
                else:
                    get_by = getattr(get_by, child)
            self.filters[filter_] = functools.partial(op_, get_by)

    def __call__(self, given_filters: dict[str, Any]) -> Generator[Any, None, None]:
        """
        Generates filters for an sqlalchemy query. Ignores unknown filters.

        Args:
            given_filters (dict[str, Any]): The filters to apply

        Yields:
            Generator[Any, None, None]: The filtered filters
        """
        for attr, filtered_by in given_filters.items():
            if attr in self.filters:
                yield self.filters[attr](filtered_by)


class OrderByMap:
    """
    Usage
    ------
    ```
    order_by_mapper = OrderByMap({
        "opponent_type": 'Opponent.type',  # Order by a column
        "wins": 'wins', # Order by a label
        }, 'your_models_module.models')

    # Generate sql
    sql.select(
        Opponent.id, sql.func.count(Game.winner_id == Opponent.id).label('wins')
    ).order_by(*order_by_mapper('opponent_type,-wins'))
    ```
    Will generate sql like:
    `
    SELECT opponents.id, COUNT(games.winner_id = opponents.id) AS wins FROM
    opponents ORDER BY opponents.type ASC, wins DESC
    `

    + The `your_models_module.models` is the module where the models are defined.
    + The order_by column may also be a label.
    """
    order_by_attributes: dict[str, Any]

    def __init__(self, order_by_attributes: dict[str, Any], import_from: str) -> None:
        module = importlib.import_module(import_from)
        self.order_by_attributes = {}
        for attr, column in order_by_attributes.items():
            if "." in column:
                model, model_attr = column.split('.')
                order_by = getattr(getattr(module, model), model_attr)
            else:
                order_by = column

            self.order_by_attributes[attr] = order_by

    def __call__(self, order_by: str):
        """
        Generates order_by for an sqlalchemy query. Ignores unknown order_by.

        Example:
        ```
            sql = select(Opponent).order_by(*self.order_by_mapper('type,-wins'))
        ```
        will generate sql like: `SELECT * FROM opponents ORDER BY type ASC, wins DESC`

        Args:
            order_by (str): The order_by to apply. May be prefixed with `-` to indicate
            descending order.

        Yields:
            Generator[Any, None, None]: Generated order_by expressions

        """
        for attr in order_by.split(','):
            if attr.startswith("-"):
                order = 'desc'
                attr = attr[1:]
            else:
                order = 'asc'
            if attr in self.order_by_attributes:
                if order == 'desc':
                    yield desc(self.order_by_attributes[attr])
                else:
                    yield self.order_by_attributes[attr]
            else:
                raise OrderByException(f"Unknown order_by attribute: {attr}")
