"""Test the filter class"""

import operator

import pytest
from sqlalchemy import UnaryExpression
from sqlalchemy.sql.elements import _textual_label_reference
from sqlalchemy.sql.operators import desc_op

from alchemical_storage.filter import FilterMap, OrderByMap
from alchemical_storage.filter.exc import OrderByException

from .models import Model

# pylint: disable=too-few-public-methods


class TestFilterMap:
    """Test the FilterMap class"""

    def test_init_initializes_filter_expressions(self):
        """Test the filter class"""
        filter_instance = FilterMap(
            {
                "filter_name": 'Model.attr',
                "filter_name2": ('Model.attr2', operator.ge,),
            }, 'tests.models'
        )
        # pylint: disable=comparison-with-callable
        assert filter_instance.filters['filter_name'].func == operator.eq
        assert filter_instance.filters['filter_name'].args[0] == Model.attr

        assert filter_instance.filters['filter_name2'].func == operator.ge
        assert filter_instance.filters['filter_name2'].args[0] == Model.attr2


class TestOrderByMap:
    """Test the OrderByMap class"""

    def test_init_raises_exception_for_invalid_order_by(self):
        """
        Test that the order by map class raises an attribute exception for invalid class or class
        attribute
        """
        with pytest.raises(AttributeError):
            OrderByMap({'order_by_name': 'Model.bad'}, 'tests.models')

    def test_call_yields_list_of_order_by_expressions_as_columns(self):
        """Test that the order by map class yields a list of order by Model column expressions"""
        order_by_instance = OrderByMap({
            'order_by_name': 'Model.attr',
            'order_by_name2': 'Model.attr2',
        }, 'tests.models')
        order_by_expressions = order_by_instance(
            'order_by_name,-order_by_name2')
        actual = list(order_by_expressions)

        # pylint: disable=comparison-with-callable
        assert len(actual) == 2
        assert actual[0] == Model.attr
        assert isinstance(actual[1], UnaryExpression)
        assert actual[1].element == Model.attr2
        assert actual[1].modifier == desc_op

    def test_call_yields_list_of_order_by_expressions_as_label(self):
        """Test that the order by map class yields a list of order by label expressions"""
        order_by_instance = OrderByMap({
            'order_by_name': 'col_label',
            'order_by_name2': 'exp_label',
        }, 'tests.models')
        actual = list(order_by_instance('order_by_name,-order_by_name2'))
        # pylint: disable=comparison-with-callable
        assert len(actual) == 2
        assert actual[0] == 'col_label'
        assert isinstance(actual[1], UnaryExpression)
        assert isinstance(actual[1].element, _textual_label_reference)
        assert actual[1].element.element == 'exp_label'
        assert actual[1].modifier == desc_op

    def test_call_raises_exception_when_order_by_query_param_is_invalid(
            self
    ):
        """
        Test that the order by map class raises an exception when the order by query param is
        invalid
        """
        order_by_instance = OrderByMap({
            'order_by_name': 'Model.attr',
            'order_by_name2': 'Model.attr2',
        }, 'tests.models')
        with pytest.raises(OrderByException, match='^(Unknown order_by attribute: invalid_param)$'):
            list(order_by_instance('order_by_name,invalid_param'))
