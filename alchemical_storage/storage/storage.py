"""Module containing the storage protocol and a database storage implementation."""

import abc
import functools
from typing import Any, Generic, Iterable, Optional, Sequence, Type, TypeVar

import sqlalchemy as sql
from marshmallow_sqlalchemy import SQLAlchemySchema
from sqlalchemy.orm import DeclarativeBase, Session
from typing_extensions import deprecated

from alchemical_storage.storage.index import DatabaseIndex
from alchemical_storage.visitor import StatementVisitor

from .exc import ConflictError, NotFoundError

AlchemyModel = TypeVar("AlchemyModel", bound=DeclarativeBase)


class StorageABC(abc.ABC, Generic[AlchemyModel]):
    """Resource storage protocol."""

    @abc.abstractmethod
    def get(self, identity: Any) -> AlchemyModel:
        """Get a resource from storage.

        Arguments:
            identity: The description

        Returns:
            A model that can be serialized to output for api

        """

    @abc.abstractmethod
    def index(self, **kwargs) -> list[AlchemyModel]:
        """Get a list of resources from storage.

        Arguments:
            **kwargs: Parameters to pass to the statement visitors.

        Returns:
            A list of models that can be serialized to output for api.

        """

    @abc.abstractmethod
    def count(self, **kwargs) -> int:
        """Count resources in storage.

        Arguments:
            **kwargs: Parameters to pass to the statement visitors.

        Returns:
            The count of resources in storage.

        """

    @abc.abstractmethod
    def put(self, identity: Any, data: dict[str, Any]) -> AlchemyModel:
        """Put a new resource to storage.

        Arguments:
            identity: The resource identifier
            data: Data that can be deserialized to create a new resource

        Returns:
            A model that can be serialized to output for api

        """

    @abc.abstractmethod
    def patch(self, identity: Any, data: dict[str, Any]) -> AlchemyModel:
        """Update a resource in storage.

        Arguments:
            identity: The resource identifier
            data: Data that can be deserialized to update the resource

        Returns:
            A model that can be serialized to output for api

        """

    @abc.abstractmethod
    def delete(self, identity: Any) -> AlchemyModel:
        """Delete a resource from storage.

        Arguments:
            identity: The resource identifier

        Returns:
            A model that can be serialized to output for api

        """

    @abc.abstractmethod
    def __contains__(self, identity: Any) -> bool:
        """Checks if resource identified by ``identity`` exists in storage.

        Arguments:
            identity: The resource identifier

        Returns:
            Whether the resource exists in storage

        """


class DatabaseStorage(StorageABC, DatabaseIndex, Generic[AlchemyModel]):
    """SQLAlchemy model storage in sql database.

    Arguments:
        session: The SQLAlchemy session to use for database operations
        entity: The SQLAlchemy model to use for database operations
        storage_schema: The marshmallow schema to use for
            serialization

    Keyword Arguments:
        primary_key: The primary key of the entity (defaults to "slug")
        statement_visitors: List of statement visitors to apply to all statements (
            defaults to [])

    """

    session: Session
    entity: Type[AlchemyModel]
    storage_schema: SQLAlchemySchema

    def __init__(
        self,
        session,
        entity: Type[AlchemyModel],
        storage_schema: SQLAlchemySchema,
        primary_key: str | Sequence[str] = "slug",
        statement_visitors: Optional[list[StatementVisitor]] = None,
    ):
        self.session = session
        self.entity = entity
        self.storage_schema = storage_schema
        self._statement_visitors = statement_visitors or []
        if isinstance(primary_key, str):
            self._attr = [primary_key]
        else:
            self._attr = list(primary_key)
        DatabaseIndex.__init__(
            self,
            session,
            entity,
            lambda entity: getattr(entity, self._attr[0]),
            statement_visitors=statement_visitors,
        )

    @staticmethod
    def _convert_identity(func):
        """Ensures that the identity of the resource is passed to the decorated function
        as a tuple."""

        @functools.wraps(func)
        def decorator(*args, **kwargs):
            argslist = list(args)
            identity_index = int(isinstance(args[0], StorageABC))
            identity = args[identity_index]
            if not isinstance(identity, Iterable) or isinstance(identity, (str, bytes)):
                identity = (identity,)
            else:
                identity = tuple(identity)
            argslist[identity_index] = identity
            return func(*argslist, **kwargs)

        return decorator

    @_convert_identity
    def get(self, identity: Any, **kwargs) -> AlchemyModel:
        """Get an AlchemyModel instance based on the given identity from the database.

        Arguments:
            identity: The unique identifier of the model to retrieve.
            **kwargs: Additional keyword arguments that may be used by statement
                visitors.

        Returns:
            The retrieved model instance. Adding this temporarily as a test to make sure
            the text wraps.

        Raises:
            NotFoundError: If no model instance matching the identity is found.

        """
        stmt = sql.select(self.entity).where(
            *(
                getattr(self.entity, _attr) == id
                for _attr, id in zip(self._attr, identity)
            )
        )
        for visitor in self._statement_visitors:
            stmt = visitor.visit_statement(stmt, kwargs)
        if model := self.session.execute(stmt).scalars().first():
            return model
        raise NotFoundError

    def index(self, **kwargs) -> list[AlchemyModel]:
        """Get a list of AlchemyModel instances from the database.

        Arguments:
            **kwargs: Arbitrary keyword arguments used to manipulate the results.

        Returns:
            A list of AlchemyModel instances.

        """
        # Ignore type error because the return type will always be a list of
        # Model instances
        return DatabaseIndex.get(self, **kwargs)  # type: ignore[return-value]

    @deprecated("Use count instead.")
    def count_index(self, **kwargs) -> int:
        return DatabaseIndex.count(self, **kwargs)

    def count(self, **kwargs) -> int:
        """Count the number of rows in the database.

        Arguments:
            **kwargs: Arbitrary keyword arguments used to manipulate the count result.

        Returns:
            The number of rows in the database.

        """
        return DatabaseIndex.count(self, **kwargs)

    @_convert_identity
    def put(self, identity: Any, data: dict[str, Any]) -> AlchemyModel:
        """Inserts a new row into the database with the given `identity`.

        Arguments:
            identity: The unique identifier for the new record.
            data: A dictionary containing the data to be stored.

        Returns:
            The newly created and stored model instance.

        Raises:
            ConflictError: If a record with the given identity already exists in the
                storage.

        Note:
            You still must persist the changes to the database by calling
            ``session.commit()`` or equivalent.

        """
        if identity in self:
            raise ConflictError
        data = {**data, **dict(zip(self._attr, identity))}
        new = self.storage_schema.load(data)
        self.session.add(new)
        self.session.flush()
        return new

    @_convert_identity
    def patch(self, identity: Any, data: dict[str, Any]) -> AlchemyModel:
        """Partially updates an existing record identified by `identity` with the
        provided `data`.

        Arguments:
            identity: The unique identifier of the record to be updated.
            data: A dictionary containing the fields to be updated and
                their new values.

        Returns:
            The updated model instance.

        Raises:
            NotFoundError: If the record identified by `identity` does not exist in the
            storage.

        Note:
            You still must persist the changes to the database by calling
            ``session.commit()`` or equivalent.

        """
        if not identity in self:
            raise NotFoundError
        self.storage_schema.load(data, partial=True, instance=self.get(identity))
        self.session.flush()
        return self.get(identity)

    @_convert_identity
    def delete(self, identity: Any) -> AlchemyModel:
        """Delete a row from the database.

        Arguments:
            identity: The unique identifier of the model to be deleted.

        Returns:
            The deleted model instance.

        Raises:
            NotFoundError: If the model with the given identity is not found in the
            storage.

        """
        if not identity in self:
            raise NotFoundError
        model = self.get(identity)
        self.session.delete(model)
        return model

    @_convert_identity
    def __contains__(self, identity: Any) -> bool:
        """Check if a row with the given identity exists in the database.

        Arguments:
            identity: The unique identifier of the row to check for.

        Returns:
            True if the row exists, False otherwise.

        """
        if result := self.session.execute(
            sql.select(sql.func.count(getattr(self.entity, self._attr[0]))).where(
                *(
                    getattr(self.entity, _attr) == id
                    for _attr, id in zip(self._attr, identity)
                )
            )
        ).scalar():
            return result > 0
        return False
