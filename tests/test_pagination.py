from unittest.mock import Mock

from alchemical_storage.pagination import PaginationMap
from tests import models


class TestPaginationMap:
    def test_visit_statement_appends_limit_and_offset_to_sql_statement(
        self,
        mock_sql_statement: Mock,
    ):
        """Test that the pagination map class appends limit and offset to sql
        statement."""
        page_params = models.PageParams(5, 0)

        pagination_instance = PaginationMap("page_params", "page_size", "first_item")
        pagination_instance.visit_statement(
            mock_sql_statement, {"page_params": page_params}
        )

        mock_sql_statement.limit.assert_called_once_with(5)
        mock_sql_statement.limit.return_value.offset.assert_called_once_with(0)

    def test_visit_statement_does_nothing_if_page_params_is_not_in_params(
        self,
        mock_sql_statement: Mock,
    ):
        """Test that the pagination map class does nothing if page params is not in
        params."""
        pagination_instance = PaginationMap("page_params", "page_size", "first_item")
        pagination_instance.visit_statement(mock_sql_statement, {})

        mock_sql_statement.limit.assert_not_called()
        mock_sql_statement.offset.assert_not_called()
