"""Module defining storage services"""

import abc
import functools
from typing import Any, Generic, Iterable, Optional, Sequence, Type, TypeVar

import sqlalchemy as sql
from marshmallow_sqlalchemy import SQLAlchemySchema
from sqlalchemy.orm import DeclarativeBase, Session

from alchemical_storage.visitor import StatementVisitor

from .exc import ConflictError, NotFoundError

AlchemyModel = TypeVar("AlchemyModel", bound=DeclarativeBase)


class StorageABC(abc.ABC, Generic[AlchemyModel]):
    """Resource storage protocol"""

    @abc.abstractmethod
    def get(self, identity: Any) -> AlchemyModel:
        """
        Get a resource from storage

        Args:
            identity (Any): The description

        Returns:
            AlchemyModel: Object that can be serialized to output for api
        """

    @abc.abstractmethod
    def index(self, **kwargs) -> list[AlchemyModel]:
        """
        Get a list resources from storage

        Returns:
            list[AlchemyModel]: List of objects that can be serialized to output for api
        """

    @abc.abstractmethod
    def count_index(self, **kwargs) -> int:
        """
        Get a list resources from storage

        Returns:
            int: Count of objects in given set
        """

    @abc.abstractmethod
    def put(self, identity: Any, data: dict[str, Any]) -> AlchemyModel:
        """
        Put a new resource to storage

        Args:
            identity (Any): The resource identifier
            data (dict[str, Any]): Data that can be deserialized to Any for create

        Returns:
            AlchemyModel: Object that can be serialized to output for api
        """

    @abc.abstractmethod
    def patch(self, identity: Any, data: dict[str, Any]) -> AlchemyModel:
        """
        Update a resource in storage

        Args:
            identity (Any): The resource identifier
            data (dict[str, Any]): Data that can be deserialized to Any for update

        Returns:
            AlchemyModel: Object that can be serialized to output for api
        """

    @abc.abstractmethod
    def delete(self, identity: Any) -> AlchemyModel:
        """
        Delete a resource from storage

        Args:
            identity (Any): The resource identifier

        Returns:
            AlchemyModel: Object that can be serialized to output for api
        """

    @abc.abstractmethod
    def __contains__(self, identity: Any) -> bool:
        """
        Checks if resource identified by identity eAny

        Args:
            identity (Any): The resource identifier

        Returns:
            bool: Whether the resource exists
        """


class DatabaseStorage(StorageABC, Generic[AlchemyModel]):
    """
    SQLAlchemy model storage in sql database

    Args:
        session (Session): The SQLAlchemy session to use for database operations
        entity (Type[AlchemyModel]): The SQLAlchemy model to use for database operations
        storage_schema (SQLAlchemySchema): The marshmallow schema to use for serialization
        primary_key (str|Sequence[str]): The primary key of the entity (Optional, defaults to
            "slug")
        statement_visitors (Optional[list[StatementVisitor]]): List of statement visitors to apply
            to all statements
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

    @staticmethod
    def _convert_identity(func):
        """
        Ensures that the identity of the resource is passed to
        the decorated function as a tuple
        """

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

    def index(self, page_params=None, **kwargs) -> list[AlchemyModel]:
        stmt = sql.select(self.entity)
        for visitor in self._statement_visitors:
            stmt = visitor.visit_statement(stmt, kwargs)
        if page_params:
            stmt = stmt.limit(page_params.page_size).offset(page_params.first_item)
        return [*self.session.execute(stmt).unique().scalars().all()]

    def count_index(self, **kwargs) -> int:
        # pylint: disable=not-callable
        stmt = sql.select(sql.func.count(getattr(self.entity, self._attr[0])))
        for visitor in self._statement_visitors:
            stmt = visitor.visit_statement(stmt, kwargs)
        return self.session.execute(stmt).unique().scalar_one()

    @_convert_identity
    def put(self, identity: Any, data: dict[str, Any]) -> AlchemyModel:
        if identity in self:
            raise ConflictError
        data = {**data, **dict(zip(self._attr, identity))}
        new = self.storage_schema.load(data)
        self.session.add(new)
        self.session.flush()
        return new

    @_convert_identity
    def patch(self, identity: Any, data: dict[str, Any]) -> AlchemyModel:
        if not identity in self:
            raise NotFoundError
        self.storage_schema.load(data, partial=True, instance=self.get(identity))
        self.session.flush()
        return self.get(identity)

    @_convert_identity
    def delete(self, identity: Any) -> AlchemyModel:
        if not identity in self:
            raise NotFoundError
        model = self.get(identity)
        self.session.delete(model)
        return model

    @_convert_identity
    def __contains__(self, identity: Any) -> bool:
        if result := self.session.execute(
            sql.select(
                sql.func.count(  # pylint: disable=not-callable
                    getattr(self.entity, self._attr[0])
                )
            ).where(
                *(
                    getattr(self.entity, _attr) == id
                    for _attr, id in zip(self._attr, identity)
                )
            )
        ).scalar():
            return result > 0
        return False
