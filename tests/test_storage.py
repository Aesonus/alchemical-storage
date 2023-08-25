"""Test the database storage class"""
import pytest
import sqlalchemy as sa
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from sqlalchemy import orm
from sqlalchemy.sql.expression import ColumnElement

from alchemical_storage.filter import FilterMap
from alchemical_storage.filter.filter import OrderByMap
from alchemical_storage.join import JoinMap
from alchemical_storage.storage import DatabaseStorage
from alchemical_storage.storage.exc import ConflictError, NotFoundError
from tests import models

# pylint: disable=too-many-public-methods


class TestDatabaseStorageWithSinglePk:
    """Test the database storage class"""
    # pylint: disable=missing-class-docstring,too-few-public-methods
    @pytest.fixture
    def session(self, existing_models: list[models.Model]):
        """Create a session for testing"""
        engine = sa.create_engine('sqlite:///:memory:')
        models.Base.metadata.create_all(bind=engine)
        session = orm.sessionmaker(bind=engine)()
        session.add_all(existing_models)
        session.add_all([
            models.RelatedToModel(attr=1, model=existing_models[0]),
        ])
        session.commit()
        yield session
        session.close()
        models.Base.metadata.drop_all(bind=engine)

    @pytest.fixture
    def entity_filters(self):
        """Create a filter for the dummy model"""
        return FilterMap({
            "attr3_like": ('Model.attr3', ColumnElement.ilike),
            "related_attr": 'RelatedToModel.attr',
        }, 'tests.models')

    @pytest.fixture
    def entity_order_by(self):
        """Create an order by for the dummy model"""
        return OrderByMap({
            "attr2": 'Model.attr2',
        }, 'tests.models')

    @pytest.fixture
    def joins(self):
        """Create a join for the dummy model"""
        return JoinMap(
            {('related_attr', ): (
                'RelatedToModel',
                models.RelatedToModel.model_id == models.Model.attr
            )}, 'tests.models')

    @pytest.fixture
    def model_schema(self, session):
        """Create a dummy model schema"""
        class ModelSchema(SQLAlchemyAutoSchema):
            class Meta:
                model = models.Model
                load_instance = True
        return ModelSchema(session=session)

    @pytest.fixture
    def existing_models(self):
        """Create a dummy model"""
        return [
            models.Model(attr=1, attr2=1, attr3="test1"),
            models.Model(attr=3, attr2=3, attr3="test3")
        ]

    @pytest.fixture
    def model_storage(self, session, model_schema, joins, entity_filters, entity_order_by):
        """Create DatabaseStorage instance for a model with single primary key"""
        return DatabaseStorage(
            session, models.Model, model_schema, primary_key="attr",
            statement_visitors=[entity_filters, entity_order_by, joins]
        )

    def test_model_storage_get_raises_not_found_error_if_model_not_found(
            self, model_storage: DatabaseStorage[models.Model]):
        """Test that get raises NotFoundError if model not found"""
        with pytest.raises(NotFoundError):
            model_storage.get(2)

    def test_model_storage_get_returns_found_model(
            self, model_storage: DatabaseStorage[models.Model], existing_models):
        """Test that get returns found model"""
        model = model_storage.get(1)
        assert model.attr == 1
        assert model.attr2 == 1
        assert model.attr3 == "test1"
        assert existing_models[0] == model

    def test_model_storage_put_inserts_new_model(
            self, model_storage: DatabaseStorage[models.Model]):
        """Test that put inserts new model"""
        model = model_storage.put(2, {"attr2": 2, "attr3": "test2"})
        model_storage.session.flush()
        assert model.attr == 2
        assert model.attr2 == 2
        assert model.attr3 == "test2"
        assert model in model_storage.session

    def test_model_storage_put_raises_conflict_error_if_model_already_exists(
            self, model_storage: DatabaseStorage[models.Model]):
        """Test that put raises ConflictError if model already exists"""
        with pytest.raises(ConflictError):
            model_storage.put(1, {"attr2": 2, "attr3": "test2"})

    def test_model_storage_patch_updates_existing_model(
            self, model_storage: DatabaseStorage[models.Model], existing_models):
        """Test that patch updates existing model"""
        model = model_storage.patch(1, {"attr2": 2, "attr3": "test2"})
        assert model.attr == 1
        assert model.attr2 == 2
        assert model.attr3 == "test2"
        assert existing_models[0] == model

    def test_model_storage_patch_raises_not_found_error_if_model_not_found(
            self, model_storage: DatabaseStorage[models.Model]):
        """Test that patch raises NotFoundError if model not found"""
        with pytest.raises(NotFoundError):
            model_storage.patch(2, {"attr2": 2, "attr3": "test2"})

    def test_model_storage_delete_deletes_model(
            self, model_storage: DatabaseStorage[models.Model], existing_models):
        """Test that delete deletes model"""
        model_storage.delete(1)
        model_storage.session.flush()
        assert existing_models[0] not in model_storage.session

    def test_model_storage_index_returns_filtered_list_of_models(
            self, model_storage: DatabaseStorage[models.Model]):
        """Test that index returns filtered list of models"""
        assert model_storage.index(attr3_like="%notfound%") == []

    def test_model_storage_index_returns_filtered_list_of_models_having_join_filters(
            self, model_storage: DatabaseStorage[models.Model], existing_models):
        """Test that index returns filtered list of models having related"""
        assert model_storage.index(related_attr=1) == [existing_models[0]]

    def test_model_storage_index_returns_list_of_models(
            self, model_storage: DatabaseStorage[models.Model], existing_models):
        """Test that index returns list of models"""
        actual = model_storage.index()
        assert actual == [existing_models[0], existing_models[1]]

    def test_model_storage_index_returns_list_of_models_with_pagination(
        self, model_storage: DatabaseStorage[models.Model], existing_models
    ):
        """Test that index returns list of models with pagination"""
        assert model_storage.index(
            page_params=models.PageParams(5, 0)) == existing_models
        assert model_storage.index(
            page_params=models.PageParams(5, 1)) == [existing_models[1]]

    def test_model_storage_returns_ordered_list_of_models(
        self, model_storage: DatabaseStorage[models.Model], existing_models
    ):
        """Test that index returns ordered list of models"""
        assert model_storage.index(
            order_by="-attr2") == list(reversed(existing_models))

    @pytest.mark.parametrize("filters, expected_count", [
        ({}, 2),
        ({"attr3_like": "%notfound%"}, 0),
        ({"attr3_like": "%test%"}, 2),
        ({'related_attr': 1}, 1),
    ])
    def test_model_storage_count_index_returns_count_of_models(
            self, model_storage: DatabaseStorage[models.Model], filters, expected_count):
        """Test that count_index returns count of models"""
        assert model_storage.count_index(**filters) == expected_count


class TestDatabaseStorageWithCompositePk:
    """Tests for composite pk models"""
    # pylint: disable=missing-class-docstring,too-few-public-methods
    @pytest.fixture
    def session(self, existing_models: list[models.CompositePkModel]):
        """Create a session for testing"""
        engine = sa.create_engine('sqlite:///:memory:')
        models.Base.metadata.create_all(bind=engine)
        session = orm.sessionmaker(bind=engine)()
        session.add_all(existing_models)
        session.commit()
        yield session
        session.close()
        models.Base.metadata.drop_all(bind=engine)

    @pytest.fixture
    def existing_models(self):
        """Create a dummy model"""
        return [
            models.CompositePkModel(attr=1, attr2=1, attr3="test1"),
            models.CompositePkModel(attr=1, attr2=2, attr3="test2"),
        ]

    @pytest.fixture
    def entity_order_by(self):
        """Create an order by for the dummy model"""
        return OrderByMap({
            "attr": 'CompositePkModel.attr',
            "attr2": 'CompositePkModel.attr2',
        }, 'tests.models')

    @pytest.fixture
    def entity_filters(self):
        """Create a filter for the dummy model"""
        return FilterMap({
            "attr3_like": ('CompositePkModel.attr3', ColumnElement.ilike),
        }, 'tests.models')

    @pytest.fixture
    def model_storage(self,
                      session,
                      model_schema,
                      entity_filters,
                      entity_order_by):
        """Create DatabaseStorage instance for a model with composite primary key"""
        return DatabaseStorage(session,
                               models.CompositePkModel,
                               model_schema,
                               primary_key=("attr", "attr2"),
                               statement_visitors=[
                                   entity_filters, entity_order_by]
                               )

    @pytest.fixture
    def model_schema(self, session):
        """Create a dummy model schema"""
        class ModelSchema(SQLAlchemyAutoSchema):
            class Meta:
                model = models.CompositePkModel
                load_instance = True
        return ModelSchema(session=session)

    def test_model_storage_get_raises_not_found_error_if_model_not_found(
            self, model_storage: DatabaseStorage[models.CompositePkModel]):
        """Test that get raises NotFoundError if model not found"""
        with pytest.raises(NotFoundError):
            model_storage.get((1, 3))

    def test_model_storage_get_returns_found_model(
            self, model_storage: DatabaseStorage[models.CompositePkModel], existing_models):
        """Test that get returns found model"""
        model = model_storage.get((1, 1))
        assert model.attr == 1
        assert model.attr2 == 1
        assert model.attr3 == "test1"
        assert model == existing_models[0]

    def test_model_storage_put_inserts_new_model(
            self, model_storage: DatabaseStorage[models.CompositePkModel]):
        """Test that put inserts new model"""
        model = model_storage.put((1, 3), {"attr3": "test2"})
        assert model.attr == 1
        assert model.attr2 == 3
        assert model.attr3 == "test2"
        model_storage.session.flush()
        assert model in model_storage.session

    def test_model_storage_put_raises_conflict_error_if_model_already_exists(
            self, model_storage: DatabaseStorage[models.CompositePkModel]):
        """Test that put raises ConflictError if model already exists"""
        with pytest.raises(ConflictError):
            model_storage.put((1, 1), {"attr3": "test2"})

    def test_model_storage_patch_updates_existing_model(
            self, model_storage: DatabaseStorage[models.CompositePkModel], existing_models):
        """Test that patch updates existing model"""
        model = model_storage.patch(
            (1, 1), {"attr3": "test2"})
        assert model.attr == 1
        assert model.attr2 == 1
        assert model.attr3 == "test2"
        assert existing_models[0] == model

    def test_model_storage_patch_raises_not_found_error_if_model_not_found(
            self, model_storage: DatabaseStorage[models.CompositePkModel]):
        """Test that patch raises NotFoundError if model not found"""
        with pytest.raises(NotFoundError):
            model_storage.patch((1, 3), {"attr3": "test2"})

    def test_model_storage_delete_deletes_model(
            self, model_storage: DatabaseStorage[models.CompositePkModel], existing_models):
        """Test that delete deletes model"""
        model_storage.delete((1, 1))
        model_storage.session.flush()
        assert existing_models[0] not in model_storage.session

    def test_model_storage_index_returns_filtered_list_of_models(
            self, model_storage: DatabaseStorage[models.CompositePkModel]):
        """Test that index returns filtered list of models"""
        assert model_storage.index(
            attr3_like="%notfound%") == []

    def test_model_storage_index_returns_list_of_models(
            self, model_storage: DatabaseStorage[models.CompositePkModel], existing_models):
        """Test that index returns list of models"""
        assert model_storage.index(
        ) == existing_models

    def test_model_storage_index_returns_ordered_list_of_models(
        self, model_storage: DatabaseStorage[models.CompositePkModel], existing_models
    ):
        """Test that index returns ordered list of models"""
        assert model_storage.index(
            order_by="attr,-attr2") == list(reversed(existing_models))

    def test_model_storage_index_returns_list_of_models_with_pagination(
            self, model_storage: DatabaseStorage[models.CompositePkModel], existing_models):
        """Test that index returns list of models with pagination"""
        assert model_storage.index(
            page_params=models.PageParams(5, 0)) == existing_models
        assert model_storage.index(
            page_params=models.PageParams(5, 1)) == [existing_models[1]]

    @pytest.mark.parametrize("filters, expected_count", [
        ({}, 2),
        ({"attr3_like": "%notfound%"}, 0),
        ({"attr3_like": "%test%"}, 2),
    ])
    def test_model_storage_count_index_returns_count_of_models(
            self, model_storage: DatabaseStorage[models.CompositePkModel],
            filters, expected_count):
        """Test that count_index returns count of models"""
        assert model_storage.count_index(
            **filters) == expected_count
