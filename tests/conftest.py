import pytest
import pytest_mock
import sqlalchemy


@pytest.fixture(scope="function")
def mock_sql_statement(mocker: pytest_mock.MockerFixture):
    """Mock the sqlalchemy statement."""
    return mocker.Mock(spec=sqlalchemy.Select)
