"""Module defining storage services"""

import abc
import functools
import itertools
from typing import Any, Generic, Iterable, Optional, TypeVar

import sqlalchemy as sql
from marshmallow_sqlalchemy import SQLAlchemySchema
from sqlalchemy.orm import Session

from alchemical_storage.filter import FilterMap
from alchemical_storage.filter.filter import OrderByMap

from .exc import ConflictError, NotFoundError

AlchemyModel = TypeVar("AlchemyModel")


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
    """SQLAlchemy model storage in sql database"""
    session: Session
    entity: AlchemyModel
    storage_schema: SQLAlchemySchema

    # pylint: disable=too-many-arguments
    def __init__(self,
                 session,
                 entity: AlchemyModel,
                 storage_schema: SQLAlchemySchema,
                 primary_key="slug",
                 filter_: Optional[FilterMap] = None,
                 order_by_mapper: Optional[OrderByMap] = None,
                 ):
        self.session = session
        self.entity = entity
        self.storage_schema = storage_schema
        self.filter = filter_
        self.order_by_mapper = order_by_mapper
        if isinstance(primary_key, str):
            self._attr = [primary_key]
        else:
            self._attr = list(primary_key)

    def _run_query(self, where=None, order_by=None, limit=None, offset=None, sql_stmt=sql.select):
        if not where:
            where = ()
        if not order_by:
            order_by = ()

        stmt = sql_stmt(
            self.entity
        ).where(*where).order_by(*order_by)
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        return self.session.execute(stmt)

    def _run_count_query(self, where=None, sql_stmt=sql.select):

        if not where:
            where = ()

        stmt = sql_stmt(
            sql.func.count(  # pylint: disable=not-callable
                getattr(self.entity, self._attr[0]))
        ).where(*where)
        return self.session.execute(stmt)

    @staticmethod
    def convert_identity(func):
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
                identity = (identity, )
            else:
                identity = tuple(identity)
            argslist[identity_index] = identity
            return func(*argslist, **kwargs)
        return decorator

    @convert_identity
    def get(self, identity: Any, **kwargs) -> AlchemyModel:
        where_clauses: list = []
        if self.filter is not None:
            where_clauses.extend(
                self.filter(kwargs)
            )
        if model := self._run_query(
            where=list(itertools.chain([
                getattr(self.entity, _attr) == id for _attr, id in zip(self._attr, identity)
            ], where_clauses)),
        ).scalars().first():
            return model
        raise NotFoundError

    def index(self, page_params=None, **kwargs) -> list[AlchemyModel]:
        where_clauses: list = []
        if self.filter is not None:
            where_clauses.extend(
                self.filter(kwargs)
            )
        query_params = {'where': where_clauses}
        if page_params:
            query_params.update(limit=page_params.page_size,
                                offset=page_params.first_item)
        if 'order_by' in kwargs:
            query_params.update(
                order_by=self.order_by_mapper(kwargs['order_by']))
        return self._run_query(**query_params).unique().scalars().all()

    def count_index(self, **kwargs) -> int:
        where_clauses: list = []
        if self.filter is not None:
            where_clauses.extend(
                self.filter(kwargs)
            )
        return self._run_count_query(where=where_clauses).unique().scalar_one()

    @convert_identity
    def put(self, identity: Any, data: dict[str, Any]) -> AlchemyModel:
        if identity in self:
            raise ConflictError
        data.update(dict(zip(self._attr, identity)))
        new = self.storage_schema.load(data)
        self.session.add(new)
        self.session.flush()
        return new

    @convert_identity
    def patch(self, identity: Any, data: dict[str, Any]) -> AlchemyModel:
        if not identity in self:
            raise NotFoundError
        self.storage_schema.load(
            data, partial=True, instance=self.get(identity))
        self.session.flush()
        return self.get(identity)

    @convert_identity
    def delete(self, identity: Any) -> AlchemyModel:
        if not identity in self:
            raise NotFoundError
        model = self.get(identity)
        self.session.delete(model)
        return model

    @convert_identity
    def __contains__(self, identity: Any) -> bool:
        return self.session.execute(  # type: ignore
            sql.select(sql.func.count(  # pylint: disable=not-callable
                getattr(self.entity, self._attr[0])  # type: ignore
            )).where(
                # type: ignore
                *(getattr(self.entity, _attr) == id for _attr, id in zip(self._attr, identity))
            )
        ).scalar() > 0
