"""SQLAlchemy models for tests"""
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
