"""Test the join module."""

from unittest.mock import Mock, call

import pytest
import pytest_mock
import sqlalchemy

from alchemical_storage.join import JoinMap
from tests import _dict_to_params
from tests.models import Model, OtherRelatedToModel, RelatedToModel

# pylint: disable=too-few-public-methods,redefined-outer-name


@pytest.fixture(scope="function")
def mock_sql_statement(mocker: pytest_mock.MockerFixture):
    """Mock the sqlalchemy statement."""
    return mocker.Mock(spec=sqlalchemy.Select)


class TestJoinVisitor:
    """Test the JoinVisitor class."""

    @pytest.mark.parametrize(
        "param_names,joins,expected_call_args_list",
        **_dict_to_params(
            {
                "one join": (
                    ("join_param",),
                    [("RelatedToModel",)],
                    [(RelatedToModel,)],
                ),
                "one join as string": (
                    ("join_param",),
                    ["RelatedToModel"],
                    [(RelatedToModel,)],
                ),
                "one join with on": (
                    ("join_param",),
                    [("RelatedToModel", "Model.related")],
                    [(RelatedToModel, Model.related)],
                ),
                "two joins": (
                    ("join_param",),
                    [("RelatedToModel",), ("OtherRelatedToModel",)],
                    [(RelatedToModel,), (OtherRelatedToModel,)],
                ),
                "two joins with on": (
                    ("join_param",),
                    [
                        ("RelatedToModel", "Model.related"),
                        ("OtherRelatedToModel", "Model.other_related"),
                    ],
                    [
                        (RelatedToModel, Model.related),
                        (OtherRelatedToModel, Model.other_related),
                    ],
                ),
                "one model relationship join": (
                    ("join_param",),
                    [("Model.related",)],
                    [(Model.related,)],
                ),
                "two model relationship join": (
                    ("join_param",),
                    [("Model.related",), ("Model.other_related",)],
                    [(Model.related,), (Model.other_related,)],
                ),
                "no joins applied": (("not_used",), [("RelatedToModel",)], []),
            }
        )
    )
    def test_visit_statement_using_string_imports(
        self, mock_sql_statement: Mock, param_names, joins, expected_call_args_list
    ):
        """Test joining a model."""
        mock_sql_statement.join.return_value = mock_sql_statement
        join_visitor = JoinMap("tests.models", param_names, *joins)
        join_visitor.visit_statement(mock_sql_statement, {"join_param": "join_param"})

        assert mock_sql_statement.join.mock_calls == [
            call(*args) for args in expected_call_args_list
        ]

    # Test the same thing as above, but using the actual classes instead of strings
    @pytest.mark.parametrize(
        "param_names,joins,expected_call_args_list",
        **_dict_to_params(
            {
                "one join": (("join_param",), [(RelatedToModel,)], [(RelatedToModel,)]),
                "one join with on": (
                    ("join_param",),
                    [(RelatedToModel, Model.related)],
                    [(RelatedToModel, Model.related)],
                ),
                "two joins": (
                    ("join_param",),
                    [(RelatedToModel,), (OtherRelatedToModel,)],
                    [(RelatedToModel,), (OtherRelatedToModel,)],
                ),
                "two joins with on": (
                    ("join_param",),
                    [
                        (RelatedToModel, Model.related),
                        (OtherRelatedToModel, Model.other_related),
                    ],
                    [
                        (RelatedToModel, Model.related),
                        (OtherRelatedToModel, Model.other_related),
                    ],
                ),
                "one model relationship join": (
                    ("join_param",),
                    [(Model.related,)],
                    [(Model.related,)],
                ),
                "two model relationship join": (
                    ("join_param",),
                    [(Model.related,), (Model.other_related,)],
                    [(Model.related,), (Model.other_related,)],
                ),
                "no joins applied": (("not_used",), [(RelatedToModel,)], []),
            }
        )
    )
    def test_visit_statement_using_classes(
        self, mock_sql_statement: Mock, param_names, joins, expected_call_args_list
    ):
        """Test joining a model."""
        mock_sql_statement.join.return_value = mock_sql_statement
        join_visitor = JoinMap("tests.models", param_names, *joins)
        join_visitor.visit_statement(mock_sql_statement, {"join_param": "join_param"})

        assert mock_sql_statement.join.mock_calls == [
            call(*args) for args in expected_call_args_list
        ]

    def test_visit_using_custom_on_criteria(
        self,
        mock_sql_statement: Mock,
    ):
        """Test joining a model."""
        expected = Model.related.and_(RelatedToModel.attr > 1)
        join_visitor = JoinMap("tests.models", ("join_param",), (expected,))
        join_visitor.visit_statement(mock_sql_statement, {"join_param": "join_param"})
        actual = mock_sql_statement.join.call_args.args[0]
        assert actual is expected

    def test_visit_using_expressions(
        self,
        mock_sql_statement: Mock,
    ):
        """Test joining a model."""
        expected = (
            RelatedToModel,
            RelatedToModel.model_id == Model.attr,
        )
        join_visitor = JoinMap("tests.models", ("join_param",), (expected,))
        join_visitor.visit_statement(mock_sql_statement, {"join_param": "join_param"})
        actual = mock_sql_statement.join.call_args.args[0]
        assert actual is expected
