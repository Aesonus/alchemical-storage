import pytest
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.sql.elements import ColumnElement

from alchemical_storage.filter import FilterMap, OrderByMap
from alchemical_storage.index.index import DatabaseIndex
from alchemical_storage.join import JoinMap
from tests import models


@pytest.fixture
def session(existing_models: list[models.Model]):
    """Create a session for testing."""
    engine = sa.create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(bind=engine)
    session = orm.sessionmaker(bind=engine)()
    session.add_all(existing_models)
    session.add_all(
        [
            models.RelatedToModel(attr=1, model=existing_models[0]),
        ]
    )
    session.commit()
    yield session
    session.close()
    # models.Base.metadata.drop_all(bind=engine)


@pytest.fixture
def entity_filters():
    """Create a filter for the dummy model."""
    return FilterMap(
        {
            "attr3_like": ("Model.attr3", ColumnElement.ilike),
            "related_attr": "RelatedToModel.attr",
        },
        "tests.models",
    )


@pytest.fixture
def entity_order_by():
    """Create an order by for the dummy model."""
    return OrderByMap(
        {
            "attr2": "Model.attr2",
        },
        "tests.models",
    )


@pytest.fixture
def joins():
    """Create a join for the dummy model."""
    return JoinMap("tests.models", ("related_attr",), ("RelatedToModel",))


@pytest.fixture
def existing_models():
    """Create a dummy model."""
    return [
        models.Model(attr=1, attr2=1, attr3="test1"),
        models.Model(attr=3, attr2=3, attr3="test3"),
    ]


class TestEntityIsModel:
    @pytest.fixture
    def database_index(self, session, joins, entity_filters, entity_order_by):
        """Create DatabaseStorage instance for a model with single primary
        key."""
        return DatabaseIndex(
            session,
            models.Model,
            lambda entity: entity.attr,
            statement_visitors=[entity_filters, entity_order_by, joins],
        )

    def test_database_index_get_returns_filtered_list_of_models(
        self,
        database_index: DatabaseIndex[models.Model],
    ):
        """Test that index returns filtered list of models."""
        assert database_index.get(attr3_like="%notfound%") == []

    def test_database_index_get_returns_filtered_list_of_models_having_join_filters(
        self, database_index: DatabaseIndex[models.Model], existing_models
    ):
        """Test that index returns filtered list of models having related."""
        assert database_index.get(related_attr=1) == [existing_models[0]]

    def test_database_index_get_returns_list_of_models(
        self, database_index: DatabaseIndex[models.Model], existing_models
    ):
        """Test that index returns list of models."""
        actual = database_index.get()
        assert actual == [existing_models[0], existing_models[1]]

    def test_database_index_get_returns_list_of_models_with_pagination(
        self, database_index: DatabaseIndex[models.Model], existing_models
    ):
        """Test that index returns list of models with pagination."""
        assert (
            database_index.get(page_params=models.PageParams(5, 0)) == existing_models
        )
        assert database_index.get(page_params=models.PageParams(5, 1)) == [
            existing_models[1]
        ]

    def test_database_index_get_returns_ordered_list_of_models(
        self, database_index: DatabaseIndex[models.Model], existing_models
    ):
        assert database_index.get(order_by="-attr2") == list(reversed(existing_models))

    @pytest.mark.parametrize(
        "filters, expected_count",
        [
            ({}, 2),
            ({"attr3_like": "%notfound%"}, 0),
            ({"attr3_like": "%test%"}, 2),
            ({"related_attr": 1}, 1),
        ],
    )
    def test_database_index_count_returns_count_of_models(
        self, database_index: DatabaseIndex[models.Model], filters, expected_count
    ):
        # I know entity is not a tuple, so I don't need to test for that in the key.
        assert database_index.count(**filters) == expected_count


class TestEntityIsTupleOfColumns:
    @pytest.fixture
    def database_index(self, session, joins, entity_filters, entity_order_by):
        """Create DatabaseStorage instance for a model with single primary
        key."""
        return DatabaseIndex(
            session,
            (models.Model.attr, models.Model.attr2, models.Model.attr3),
            lambda entity: entity[0],
            statement_visitors=[entity_filters, entity_order_by, joins],
        )

    def test_database_index_get_returns_filtered_list_of_models(
        self,
        database_index: DatabaseIndex[models.Model],
    ):
        """Test that index returns filtered list of models."""
        assert database_index.get(attr3_like="%notfound%") == []

    def test_database_index_get_returns_filtered_list_of_models_having_join_filters(
        self, database_index: DatabaseIndex[models.Model], existing_models
    ):
        """Test that index returns filtered list of models having related."""
        assert database_index.get(related_attr=1) == [
            (
                existing_models[0].attr,
                existing_models[0].attr2,
                existing_models[0].attr3,
            )
        ]

    def test_database_index_get_returns_list_of_models(
        self, database_index: DatabaseIndex[models.Model], existing_models
    ):
        """Test that index returns list of models."""
        actual = database_index.get()
        assert actual == [
            (
                existing_model.attr,
                existing_model.attr2,
                existing_model.attr3,
            )
            for existing_model in existing_models[0:2]
        ]

    def test_database_index_get_returns_list_of_models_with_pagination(
        self, database_index: DatabaseIndex[models.Model], existing_models
    ):
        """Test that index returns list of models with pagination."""
        assert database_index.get(page_params=models.PageParams(5, 0)) == [
            (
                existing_model.attr,
                existing_model.attr2,
                existing_model.attr3,
            )
            for existing_model in existing_models
        ]

        assert database_index.get(page_params=models.PageParams(5, 1)) == [
            (
                existing_models[1].attr,
                existing_models[1].attr2,
                existing_models[1].attr3,
            )
        ]

    def test_database_index_get_returns_ordered_list_of_models(
        self, database_index: DatabaseIndex[models.Model], existing_models
    ):
        assert database_index.get(order_by="-attr2") == list(
            (
                existing_model.attr,
                existing_model.attr2,
                existing_model.attr3,
            )
            for existing_model in reversed(existing_models)
        )

    @pytest.mark.parametrize(
        "filters, expected_count",
        [
            ({}, 2),
            ({"attr3_like": "%notfound%"}, 0),
            ({"attr3_like": "%test%"}, 2),
            ({"related_attr": 1}, 1),
        ],
    )
    def test_database_index_count_returns_count_of_models(
        self, database_index: DatabaseIndex[models.Model], filters, expected_count
    ):
        assert database_index.count(**filters) == expected_count
