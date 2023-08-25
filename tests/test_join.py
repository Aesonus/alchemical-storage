from unittest.mock import Mock

import pytest
import pytest_mock
import sqlalchemy

from alchemical_storage.join import JoinVisitor
from tests.models import RelatedToModel

# pylint: disable=too-few-public-methods,redefined-outer-name


@pytest.fixture(scope='function')
def mock_sql_statement(mocker: pytest_mock.MockerFixture):
    """Mock the sqlalchemy statement"""
    return mocker.Mock(spec=sqlalchemy.Select)


class TestJoinVisitor:
    """Test the JoinVisitor class"""

    @pytest.mark.parametrize("joins,expected_call_args", [
        ({('join_param',): 'RelatedToModel', }, (RelatedToModel, )),
        ({('join_param',): 'RelatedToModel.model_id', }, (RelatedToModel.model_id, )),
        ({('join_param',): ('RelatedToModel.model_id',)},
         (RelatedToModel.model_id, )),
    ])
    def test_visit_statement(
            self, mock_sql_statement: Mock,
            joins, expected_call_args
    ):
        """Test joining a model"""
        join_visitor = JoinVisitor(
            joins, 'tests.models'
        )
        join_visitor.visit_statement(
            mock_sql_statement, {'join_param': 'join_param'}
        )
        mock_sql_statement.join.assert_called_once_with(
            *expected_call_args
        )

    def test_no_join_if_missing_joinable_params(
            self, mock_sql_statement: Mock
    ):
        """Test that no join is added if the joinable params are missing"""
        join_visitor = JoinVisitor(
            {('join_param', ): 'RelatedToModel.model_id'}, 'tests.models'
        )
        join_visitor.visit_statement(
            mock_sql_statement, {}
        )
        mock_sql_statement.join.assert_not_called()
