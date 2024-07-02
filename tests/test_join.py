"""Test the join module."""

from unittest.mock import Mock, call

import pytest

import tests.models
from alchemical_storage.join import JoinMap
from tests import dict_to_params
from tests.models import Model, OtherRelatedToModel, RelatedToModel


@pytest.mark.parametrize(
    "import_from",
    [
        "tests.models",
        tests.models,
    ],
    ids=["string", "module"],
)
class TestJoinVisitor:
    """Test the JoinVisitor class."""

    @pytest.mark.parametrize(
        "param_names,joins,expected_call_args_list",
        **dict_to_params(
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
        self,
        mock_sql_statement: Mock,
        param_names,
        joins,
        expected_call_args_list,
        import_from,
    ):
        """Test joining a model."""
        mock_sql_statement.join.return_value = mock_sql_statement
        join_visitor = JoinMap(import_from, param_names, *joins)
        join_visitor.visit_statement(mock_sql_statement, {"join_param": "join_param"})

        assert mock_sql_statement.join.mock_calls == [
            call(*args) for args in expected_call_args_list
        ]

    # Test the same thing as above, but using the actual classes instead of strings
    @pytest.mark.parametrize(
        "param_names,joins,expected_call_args_list",
        **dict_to_params(
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
        self,
        mock_sql_statement: Mock,
        param_names,
        joins,
        expected_call_args_list,
        import_from,
    ):
        """Test joining a model."""
        mock_sql_statement.join.return_value = mock_sql_statement
        join_visitor = JoinMap(import_from, param_names, *joins)
        join_visitor.visit_statement(mock_sql_statement, {"join_param": "join_param"})

        assert mock_sql_statement.join.mock_calls == [
            call(*args) for args in expected_call_args_list
        ]

    def test_visit_using_custom_on_criteria(
        self, mock_sql_statement: Mock, import_from
    ):
        """Test joining a model."""
        expected = Model.related.and_(RelatedToModel.attr > 1)
        join_visitor = JoinMap(import_from, ("join_param",), (expected,))
        join_visitor.visit_statement(mock_sql_statement, {"join_param": "join_param"})
        actual = mock_sql_statement.join.call_args.args[0]
        assert actual is expected

    def test_visit_using_expressions(self, mock_sql_statement: Mock, import_from):
        """Test joining a model."""
        expected = (
            RelatedToModel,
            RelatedToModel.model_id == Model.attr,
        )
        join_visitor = JoinMap(import_from, ("join_param",), (expected,))
        join_visitor.visit_statement(mock_sql_statement, {"join_param": "join_param"})
        actual = mock_sql_statement.join.call_args.args[0]
        assert actual is expected
