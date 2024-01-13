"""Test the filter class."""

import operator
from unittest.mock import Mock

import pytest
import pytest_mock
import sqlalchemy
from sqlalchemy import BinaryExpression, UnaryExpression
from sqlalchemy.sql.elements import _textual_label_reference
from sqlalchemy.sql.operators import desc_op

from alchemical_storage.filter import FilterMap, OrderByMap
from alchemical_storage.filter.exc import OrderByException

from .models import Model

# pylint: disable=too-few-public-methods,redefined-outer-name


@pytest.fixture(scope="function")
def mock_sql_statement(mocker: pytest_mock.MockerFixture):
    """Mock the sqlalchemy statement."""
    return mocker.Mock(spec=sqlalchemy.Select)


class TestFilterMap:
    """Test the FilterMap class."""

    def test_init_initializes_filter_expressions(self):
        """Test the filter class."""
        filter_instance = FilterMap(
            {
                "filter_name": "Model.attr",
                "filter_name2": (
                    "Model.attr2",
                    operator.ge,
                ),
            },
            "tests.models",
        )
        # pylint: disable=comparison-with-callable
        assert filter_instance.filters["filter_name"].func == operator.eq
        assert filter_instance.filters["filter_name"].args[0] == Model.attr

        assert filter_instance.filters["filter_name2"].func == operator.ge
        assert filter_instance.filters["filter_name2"].args[0] == Model.attr2

    @pytest.mark.parametrize(
        "given_filters, expected_left_list, expected_right_value_list",
        [
            ({"filter_name": "testvalue"}, [Model.attr], ["testvalue"]),
            ({"filter_name2": "testvalue"}, [Model.attr2], ["testvalue"]),
            (
                {"filter_name": "testvalue", "filter_name2": "testvalue2"},
                [Model.attr, Model.attr2],
                ["testvalue", "testvalue2"],
            ),
        ],
    )
    def test_visit_statement_appends_where_clauses_for_given_filters(
        self,
        mock_sql_statement: Mock,
        expected_left_list,
        expected_right_value_list,
        given_filters,
    ):
        """Test that the filter class appends where clauses for given
        filters."""
        filter_instance = FilterMap(
            {
                "filter_name": "Model.attr",
                "filter_name2": (
                    "Model.attr2",
                    operator.ge,
                ),
            },
            "tests.models",
        )
        filter_instance.visit_statement(mock_sql_statement, given_filters)
        for actual, expected_left, expected_right_value in zip(
            mock_sql_statement.where.call_args.args,
            expected_left_list,
            expected_right_value_list,
        ):
            assert isinstance(actual, BinaryExpression)
            assert actual.left == expected_left
            assert actual.right.value == expected_right_value


class TestOrderByMap:
    """Test the OrderByMap class."""

    def test_init_raises_exception_for_invalid_order_by(self):
        """Test that the order by map class raises an attribute exception for
        invalid class or class attribute."""
        with pytest.raises(AttributeError):
            OrderByMap({"order_by_name": "Model.bad"}, "tests.models")

    def test_visit_statement_appends_order_by_clauses_for_given_order_by(
        self,
        mock_sql_statement: Mock,
    ):
        """Test that the order by map class appends order by clauses for given
        order by."""
        # pylint: disable=comparison-with-callable

        order_by_instance = OrderByMap(
            {
                "order_by_name": "Model.attr",
                "order_by_name2": "Model.attr2",
            },
            "tests.models",
        )
        order_by_instance.visit_statement(
            mock_sql_statement, {"order_by": "order_by_name,-order_by_name2"}
        )
        assert mock_sql_statement.order_by.call_args.args[0] == Model.attr
        assert isinstance(
            mock_sql_statement.order_by.call_args.args[1], UnaryExpression
        )
        assert mock_sql_statement.order_by.call_args.args[1].element == Model.attr2
        assert mock_sql_statement.order_by.call_args.args[1].modifier == desc_op

    def test_visit_statement_appends_order_by_clauses_for_given_order_by_with_label(
        self,
        mock_sql_statement: Mock,
    ):
        """Test that the order by map class appends order by clauses for given
        order by with label."""
        # pylint: disable=comparison-with-callable

        order_by_instance = OrderByMap(
            {
                "order_by_name": "col_label",
                "order_by_name2": "exp_label",
            },
            "tests.models",
        )
        order_by_instance.visit_statement(
            mock_sql_statement, {"order_by": "order_by_name,-order_by_name2"}
        )
        assert mock_sql_statement.order_by.call_args.args[0] == "col_label"
        assert isinstance(
            mock_sql_statement.order_by.call_args.args[1], UnaryExpression
        )
        assert isinstance(
            mock_sql_statement.order_by.call_args.args[1].element,
            _textual_label_reference,
        )
        assert (
            mock_sql_statement.order_by.call_args.args[1].element.element == "exp_label"
        )
        assert mock_sql_statement.order_by.call_args.args[1].modifier == desc_op

    def test_visit_statement_appends_order_by_clauses_for_given_order_by_with_label_and_attr(
        self,
        mock_sql_statement: Mock,
    ):
        """Test that the order by map class appends order by clauses for given
        order by with label and attr."""
        # pylint: disable=comparison-with-callable

        order_by_instance = OrderByMap(
            {
                "order_by_name": "col_label",
                "order_by_name2": "Model.attr",
            },
            "tests.models",
        )
        order_by_instance.visit_statement(
            mock_sql_statement, {"order_by": "order_by_name,-order_by_name2"}
        )
        assert mock_sql_statement.order_by.call_args.args[0] == "col_label"
        assert isinstance(
            mock_sql_statement.order_by.call_args.args[1], UnaryExpression
        )
        assert mock_sql_statement.order_by.call_args.args[1].element == Model.attr
        assert mock_sql_statement.order_by.call_args.args[1].modifier == desc_op

    def test_visit_statement_raises_exception_when_order_by_query_param_is_invalid(
        self,
        mock_sql_statement: Mock,
    ):
        """Test that the order by map class raises an exception when the order
        by query param is invalid."""
        order_by_instance = OrderByMap(
            {
                "order_by_name": "Model.attr",
                "order_by_name2": "Model.attr2",
            },
            "tests.models",
        )
        with pytest.raises(
            OrderByException, match="^(Unknown order_by attribute: invalid_param)$"
        ):
            order_by_instance.visit_statement(
                mock_sql_statement, {"order_by": "order_by_name,invalid_param"}
            )
