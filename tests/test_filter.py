"""Test the filter class."""

import operator
from unittest.mock import Mock

import pytest
from sqlalchemy import BinaryExpression, UnaryExpression
from sqlalchemy.sql.elements import _textual_label_reference
from sqlalchemy.sql.operators import desc_op

import tests.models
from alchemical_storage.filter import FilterMap, OrderByMap
from alchemical_storage.filter.exc import NullFilterException, OrderByException
from alchemical_storage.filter.filter import NullFilterMap
from tests import dict_to_params

from .models import Model

# pylint: disable=too-few-public-methods,redefined-outer-name


@pytest.mark.parametrize(
    "import_from",
    [
        "tests.models",
        tests.models,
    ],
    ids=["string", "module"],
)
class TestFilterMap:
    """Test the FilterMap class."""

    def test_init_initializes_filter_expressions(self, import_from):
        """Test the filter class."""
        filter_instance = FilterMap(
            {
                "filter_name": "Model.attr",
                "filter_name2": (
                    "Model.attr2",
                    operator.ge,
                ),
            },
            import_from,
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
        import_from,
    ):
        """Test that the filter class appends where clauses for given filters."""
        filter_instance = FilterMap(
            {
                "filter_name": "Model.attr",
                "filter_name2": (
                    "Model.attr2",
                    operator.ge,
                ),
            },
            import_from,
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


@pytest.mark.parametrize(
    "import_from",
    [
        "tests.models",
        tests.models,
    ],
    ids=["string", "module"],
)
class TestOrderByMap:
    """Test the OrderByMap class."""

    def test_init_raises_exception_for_invalid_order_by(self, import_from):
        """Test that the order by map class raises an attribute exception for invalid
        class or class attribute."""
        with pytest.raises(AttributeError):
            OrderByMap({"order_by_name": "Model.bad"}, "tests.models")

    def test_visit_statement_appends_order_by_clauses_for_given_order_by(
        self, mock_sql_statement: Mock, import_from
    ):
        """Test that the order by map class appends order by clauses for given order
        by."""
        # pylint: disable=comparison-with-callable

        order_by_instance = OrderByMap(
            {
                "order_by_name": "Model.attr",
                "order_by_name2": "Model.attr2",
            },
            import_from,
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
        self, mock_sql_statement: Mock, import_from
    ):
        """Test that the order by map class appends order by clauses for given order by
        with label."""
        # pylint: disable=comparison-with-callable

        order_by_instance = OrderByMap(
            {
                "order_by_name": "col_label",
                "order_by_name2": "exp_label",
            },
            import_from,
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
        self, mock_sql_statement: Mock, import_from
    ):
        """Test that the order by map class appends order by clauses for given order by
        with label and attr."""
        # pylint: disable=comparison-with-callable

        order_by_instance = OrderByMap(
            {
                "order_by_name": "col_label",
                "order_by_name2": "Model.attr",
            },
            import_from,
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
        self, mock_sql_statement: Mock, import_from
    ):
        """Test that the order by map class raises an exception when the order by query
        param is invalid."""
        order_by_instance = OrderByMap(
            {
                "order_by_name": "Model.attr",
                "order_by_name2": "Model.attr2",
            },
            import_from,
        )
        with pytest.raises(
            OrderByException, match="^(Unknown order_by attribute: invalid_param)$"
        ):
            order_by_instance.visit_statement(
                mock_sql_statement, {"order_by": "order_by_name,invalid_param"}
            )


@pytest.mark.parametrize(
    "import_from",
    [
        "tests.models",
        tests.models,
    ],
    ids=["string", "module"],
)
class TestNullFilterMap:
    """Test the NullFilterMap class."""

    @pytest.mark.parametrize(
        "given_filters,compare",
        **dict_to_params(
            {
                "filter_name is null": (
                    {"filter_name": "null"},
                    [(Model.attr, "is_")],
                ),
                "filter_name is not null": (
                    {"filter_name": "not-null"},
                    [(Model.attr, "is_not")],
                ),
                "filter_name is null, filter_name2 is not null": (
                    {"filter_name": "null", "filter_name2": "not-null"},
                    [(Model.attr, "is_"), (Model.attr2, "is_not")],
                ),
            }
        )
    )
    def test_visit_statement_appends_where_clauses_for_given_filters(
        self, mock_sql_statement: Mock, given_filters, compare, import_from
    ):
        """Test that the filter class appends where clauses for given filters."""
        filter_instance = NullFilterMap(
            {
                "filter_name": "Model.attr",
                "filter_name2": "Model.attr2",
            },
            import_from,
        )
        filter_instance.visit_statement(mock_sql_statement, given_filters)
        for actual, expected in zip(mock_sql_statement.where.call_args.args, compare):
            assert isinstance(actual, BinaryExpression)
            assert actual.left == expected[0]
            assert actual.operator.__name__ == expected[1]
            assert str(actual.right) == "NULL"

    def test_visit_statement_raises_exception_when_query_param_value_is_invalid(
        self, mock_sql_statement: Mock, import_from
    ):
        """Test that the null filter map class raises an exception when the query param
        value is invalid."""
        filter_instance = NullFilterMap(
            {
                "filter_name": "Model.attr",
                "filter_name2": "Model.attr2",
            },
            import_from,
        )
        with pytest.raises(
            NullFilterException,
            match="^(Unknown filter value: 'unknown_value' for `filter_name`)$",
        ):
            filter_instance.visit_statement(
                mock_sql_statement, {"filter_name": "unknown_value"}
            )

    def test_visit_statement_does_nothing_if_filter_is_not_in_filters(
        self, mock_sql_statement: Mock, import_from
    ):
        """Test that the null filter map class does nothing if the filter is not in the
        filters."""
        filter_instance = NullFilterMap(
            {
                "filter_name": "Model.attr",
                "filter_name2": "Model.attr2",
            },
            import_from,
        )
        filter_instance.visit_statement(mock_sql_statement, {"filter_name3": "null"})
        mock_sql_statement.where.assert_called_once_with()
