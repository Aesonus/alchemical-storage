"""SQLAlchemy models for tests"""
import sqlalchemy as sqla
from sqlalchemy import orm

# pylint: disable=too-few-public-methods


class Base(orm.DeclarativeBase):
    """Base class for all models"""


class Model(Base):
    """Dummy model class"""
    __tablename__ = 'models'
    attr: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    attr2: orm.Mapped[int]
    attr3: orm.Mapped[str]
    related = orm.relationship(
        'RelatedToModel', uselist=True, back_populates='model', cascade='all, delete-orphan')
    other_related = orm.relationship(
        'OtherRelatedToModel', uselist=True, back_populates='model', cascade='all, delete-orphan')


class RelatedToModel(Base):
    """Dummy model class"""
    __tablename__ = 'related_to_models'
    attr: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    model_id: orm.Mapped[int] = orm.mapped_column(sqla.ForeignKey(Model.attr))
    model = orm.relationship(Model, back_populates='related')


class OtherRelatedToModel(Base):
    """Dummy model class"""
    __tablename__ = 'other_related_to_models'
    attr: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    model_id: orm.Mapped[int] = orm.mapped_column(sqla.ForeignKey(Model.attr))
    model = orm.relationship(Model, back_populates='other_related')


class CompositePkModel(Base):
    """Dummy model class"""
    __tablename__ = 'composite_pk_models'
    attr: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    attr2: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    attr3: orm.Mapped[str]


class PageParams:
    """Class for page params"""

    def __init__(self, page_size: int, first_item: int) -> None:
        self.page_size = page_size
        self.first_item = first_item
