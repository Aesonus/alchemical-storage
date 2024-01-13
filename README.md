# Quickstart


__alchemical-storage__ is a library intended to bridge CRUD operations with SQLAlchemy query constructs

## Install
```pip install alchemical-storage```

## Basic Usage
`alchemical-storage` assumes that you have set up a session (or scoped_session) for your database. This is assumed to have been imported as `session` in the following example. The table for the defined model is also assumed to be in the database.

1. Set up the model.

    ```python
    """package/models.py"""
    from sqlalchemy import orm

    class Model(orm.DeclarativeBase):
        """Model class"""
        __tablename__ = 'models'
        attr: orm.Mapped[int] = orm.mapped_column(primary_key=True)
        attr2: orm.Mapped[int]
        attr3: orm.Mapped[str]
    ```

2. Set up the storage schema. The Meta class in the schema should set load_instance to `True`.

    ```python
    """package/schema.py"""
    from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
    from package import Model

    class ModelSchema(SQLAlchemyAutoSchema):
        """Model storage schema"""
        class Meta:
            model = Model
            load_instance = True
    ```

3. Create a DatabaseStorage instance. Set the `primary_key` keyword argument (defaults to 'slug') to the primary key of the model.

    ```python
    """___main___.py"""
    from package import models
    from package.schema import ModelSchema
    storage = DatabaseStorage(
        session, models.Model, ModelSchema, primary_key="attr",)
    ```

4. Use the DatabaseStorage instance.

    ```python
    # __main__.py continued...

    storage.get(1)  # Gets a record from the database
    storage.put(2, {'attr2': 1, 'attr3': 'test'})  # Puts a record to the database
    storage.patch(1, {'attr2': 42})  # Update a record in the database
    storage.delete(1)  # Delete a record from the database
    storage.index()  # Get an index of records from the database
    ```

5. Commit changes to the database.

    ```python
    session.commit()
    ```

## License
MIT License. See LICENSE file for more details.