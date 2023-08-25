"""Classes for adding joins to sqlalchemy queries."""

import importlib
from typing import Any

from alchemical_storage.visitor import StatementVisitor, T


class JoinMap(StatementVisitor):
    """
    Initialize the join mapper

    Args:
        joins (dict[tuple[str, ...], str | tuple[Any, ...]]): A dictionary of joins
        import_from (str): The module to import Model classes from

    Example:
        ::
            join_visitor = JoinMap({
                ('join_param',): 'RelatedToModel',
            }, 'your_models_module.models')

    Note:
        + The ``your_models_module.models`` is the module where the models are defined.
        + The ``('join_param',)`` is a tuple of attributes that will trigger the join.
        + The ``'RelatedToModel'`` is the model to join. It can be a string or a tuple of
            strings. If it is a tuple, the last element is the join condition and the
            first elements are the attributes to join on.
    """

    def __init__(self, joins: dict[tuple[str, ...], str | tuple[Any, ...]], import_from: str):
        self.__module = importlib.import_module(import_from)
        self.joins = {}
        for attrs, join in joins.items():
            if isinstance(join, str):
                join = (join, )
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
