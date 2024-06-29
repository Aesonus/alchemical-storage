Usage Guide
-----------
This guide assumes that you have prior knowledge of SQLAlchemy and Marshmallow-SQLAlchemy. If you are not familiar with these libraries, please refer to their documentation first.

We will be using SQLAlchemy version 2, but this library should also work with SQLAlchemy version 1.

Database Index
==============
The :class:`DatabaseIndex <alchemical_storage.storage.index.DatabaseIndex>` class is used to retreive an index of items from the database. It can also use customizable filters, sorting, pagination, and more.

Setup
~~~~~
First, we will need a model class to represent the database table. In this example, we will use a table called ``Items`` and the model class will look like this:

.. code-block:: python
    :caption: models.py

    import datetime
    from sqlalchemy import orm

    class Item(orm.DeclarativeBase):
        __tablename__ = 'Items'

        id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
        name: orm.Mapped[str]
        price: orm.Mapped[float]
        department_id: orm.Mapped[int]
        deleted_at: orm.Mapped[datetime.datetime | None]

The next step is to create an instance of the :class:`DatabaseIndex <alchemical_storage.storage.index.DatabaseIndex>` class. This class requires a SQLAlchemy session, a model class and a column to use for counting the total number of items. In this case, we will use the ``id`` column.

.. code-block:: python
    :caption: index.py

    from alchemical_storage.storage.index import DatabaseIndex
    from .models import Item
    from .session import session # Assuming that the session is already
                                 # created in a separate file

    index = DatabaseIndex(session, Item, Item.id)

Getting Items
~~~~~~~~~~~~~

To get all items from the database, you can use the :meth:`DatabaseIndex.get <alchemical_storage.storage.DatabaseIndex.get>` method. This method returns a list of items.

.. code-block:: python
    :caption: index.py

    items = index.get()

Getting the Total Number of Items
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To get the total number of items in the database, you can use the :meth:`DatabaseIndex.count <alchemical_storage.storage.DatabaseIndex.count>` method.

.. code-block:: python
    :caption: index.py

    total_items = index.count()

Using Filters
~~~~~~~~~~~~~

If we want to filter items based on certain criteria, we can set up the DatabaseIndex with filters. We can define several different types of filters, described below.

.. _UsingFilterMap:

``FilterMap``
^^^^^^^^^^^^^

In this example, we want to be able to filter by the item's name, department ID, price greater than a certain value, and price less than a certain value. The :class:`FilterMap <alchemical_storage.filter.FilterMap>` class is a general purpose class that can be used to define several different types of filters:

.. code-block:: python
    :caption: index_with_filters.py

    from alchemical_storage.storage.index import DatabaseIndex
    from .models import Item
    from .session import session # Assuming that the session is already
                                 # created in a separate file

    from alchemical_storage.filter import FilterMap

    import operator
    from sqlalchemy import ColumnElement

    filters = FilterMap({
        "name": ("Item.name", ColumnElement.ilike),
        "department_id": "Item.department_id",
        "price_gt": ("Item.price", operator.gt),
        "price_lt": ("Item.price", operator.lt),
    }, "base_package.models")


As we can see, the :class:`FilterMap <alchemical_storage.filter.FilterMap>` class takes a dictionary of filters, where the key is the name of the filter and the value is a tuple containing the column name and the operator to use for the filter; if a string is given instead of a tuple, the operator is assumed to be ``operator.eq``. The last argument is the package name where the model class or classes are located.

.. warning::
    The ``sqlalchemy.ColumnElement.is_not`` operator does not behave as expected when using the :class:`FilterMap <alchemical_storage.filter.FilterMap>` class. If you need to use this operator, see the :ref:`UsingNullFilterMap` section below.

Now we can use the :meth:`DatabaseIndex.get <alchemical_storage.storage.DatabaseIndex.get>` method with filters:

.. code-block:: python
    :caption: index_with_filters.py

    # Pass the FilterMap instance to the DatabaseIndex in the constructor
    # using a list or sequence
    index = DatabaseIndex(session, Item, Item.id, [filters])

    # Get items with the specified filters
    items = index.get(
        name="%apple%",
        department_id=1,
        price_gt=1.0,
        price_lt=10.0
    )

This would translate to this in SQL:

.. code-block:: sql
    :caption: SQL Query

    SELECT id, name, price, department_id, deleted_at FROM Items
    WHERE name ILIKE '%apple%'
    AND department_id = 1
    AND price > 1.0
    AND price < 10.0


.. _UsingNullFilterMap:

``NullFilterMap``
^^^^^^^^^^^^^^^^^

Now let's say we want to be able to filter by whether the item has been deleted or not. We can use the :class:`NullFilterMap <alchemical_storage.filter.NullFilterMap>` class to define filters that check if a column is null or not:

.. code-block:: python
    :caption: index_with_null_filters.py

    from alchemical_storage.storage.index import DatabaseIndex
    from .models import Item
    from .session import session # Assuming that the session is already
                                 # created in a separate file

    from alchemical_storage.filter import NullFilterMap

    filters = NullFilterMap({
        "deleted": "Item.deleted_at",
    }, "base_package.models")

The :class:`NullFilterMap <alchemical_storage.filter.NullFilterMap>` class takes a dictionary of filters, where the key is the name of the filter and the value is the column name. The last argument is the package name where the model class or classes are located.

Now we can use the :meth:`DatabaseIndex.get <alchemical_storage.storage.DatabaseIndex.get>` method with filters:

.. code-block:: python
    :caption: index_with_null_filters.py

    # Pass the NullFilterMap instance to the DatabaseIndex in the constructor
    # using a list or sequence
    index = DatabaseIndex(session, Item, Item.id, [filters])

    # Get items with the specified filters
    items = index.get(
        deleted="null" # or "not-null" to get items that are not deleted
    )

This would translate to this in SQL:

.. code-block:: sql
    :caption: SQL Query

    SELECT id, name, price, department_id, deleted_at FROM Items
    WHERE deleted_at IS NULL

.. note:: The value of the filter that corresponds to null and not null can be set by passing a 2-tuple to the :class:`NullFilterMap <alchemical_storage.filter.NullFilterMap>` constructor using the ``null_identifiers`` keyword argument, where the first element is the value for null and the second element is the value for not null. Only string values are allowed.

Sorting Results
~~~~~~~~~~~~~~~

To sort the results, we need to use the :class:`OrderByMap <alchemical_storage.filter.OrderByMap>` class:

.. code-block:: python
    :caption: index_with_order_by.py

    from alchemical_storage.storage.index import DatabaseIndex
    from .models import Item
    from .session import session # Assuming that the session is already
                                 # created in a separate file

    from alchemical_storage.filter import OrderByMap

    order_by = OrderByMap({
        "name": "Item.name",
        "price": "Item.price",
    }, "base_package.models")

The :class:`OrderByMap <alchemical_storage.filter.OrderByMap>` class takes a dictionary of columns to sort by, where the key is the name that will be used to indicate a sort field and the value is the column. The last argument is the package name where the model class or classes are located.

Now we can use the :meth:`DatabaseIndex.get <alchemical_storage.storage.DatabaseIndex.get>` method with sorting:

.. code-block:: python
    :caption: index_with_order_by.py

    # Pass the OrderByMap instance to the DatabaseIndex in the constructor
    # using a list or sequence
    index = DatabaseIndex(session, Item, Item.id, [order_by])

    # Get items with the specified sorting
    items = index.get(
        order_by="name,-price"
    )

This would translate to this in SQL:

.. code-block:: sql
    :caption: SQL Query

    SELECT id, name, price, department_id, deleted_at FROM Items
    ORDER BY name ASC, price DESC

As we can see, we can specify multiple columns to sort by, separated by commas. If we want to sort in descending order, we can prefix the column name with a minus sign. The ``order_by`` keyword argument triggers the sorting.

Pagination
~~~~~~~~~~

To allow for the paginatination of the results, we need to use the :class:`PaginationMap <alchemical_storage.pagination.PaginationMap>` class:

.. code-block:: python
    :caption: index_with_pagination.py

    from alchemical_storage.storage.index import DatabaseIndex
    from .models import Item
    from .session import session # Assuming that the session is already
                                 # created in a separate file

    from alchemical_storage.pagination import PaginationMap

    pagination = PaginationMap({
        "pagination",
        "page_size",
        "first_item",
    })

    # Pass the PaginationMap instance to the DatabaseIndex in the
    # constructor using a list or sequence
    index = DatabaseIndex(session, Item, Item.id, [pagination])

    # Get items with the specified pagination
    items = index.get(
        pagination=SimpleNamespace(page_size=10, first_item=0)
    )

The :class:`PaginationMap <alchemical_storage.pagination.PaginationMap>` class requires the name of the pagination keyword argument passed to the :meth:`DatabaseIndex.get <alchemical_storage.storage.DatabaseIndex.get>` method.

The :class:`PaginationMap <alchemical_storage.pagination.PaginationMap>` class will normally expect an object to be passed to the :meth:`DatabaseIndex.get <alchemical_storage.storage.DatabaseIndex.get>` method pagination parameter and will access the ``page_size`` and ``first_item`` attributes to determine the pagination.

We could also accept a dictionary with the pagination parameters instead of an object by changing the ``getter_func`` keyword argument to ``operator.getitem``:

.. code-block:: python
    :caption: index_with_pagination.py

    from alchemical_storage.storage.index import DatabaseIndex
    from .models import Item
    from .session import session # Assuming that the session is already
                                 # created in a separate file

    from alchemical_storage.pagination import PaginationMap

    import operator

    pagination = PaginationMap({
            "pagination",
            "page_size",
            "first_item",
        },
        # Use operator.getitem to access the pagination parameters
        getter_func=operator.getitem
    )

    # Pass the PaginationMap instance to the DatabaseIndex in the
    # constructor using a list or sequence
    index = DatabaseIndex(session, Item, Item.id, [pagination])

    # Get items with the specified pagination
    items = index.get(
        pagination={"page_size": 10, "first_item": 0}
    )

This would translate to this in SQL:

.. code-block:: sql
    :caption: SQL Query

    SELECT id, name, price, department_id, deleted_at FROM Items
    LIMIT 10 OFFSET 0

Joins
~~~~~

Now lets look at joins. For this example, we will use two tables: ``Items`` and ``Departments``. The ``Items`` table has a foreign key to the ``Departments`` table. The model classes will look like this:

.. code-block:: python
    :caption: models.py

    import datetime
    from sqlalchemy import orm

    class Item(orm.DeclarativeBase):
        __tablename__ = 'Items'

        id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
        name: orm.Mapped[str]
        price: orm.Mapped[float]
        department_id: orm.Mapped[int]
        deleted_at: orm.Mapped[datetime.datetime | None]
        department: orm.Mapped[Department] = orm.relationship(
            "Department",
            back_populates="items",
        )

    class Department(orm.DeclarativeBase):
        __tablename__ = 'Departments'

        id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
        name: orm.Mapped[str]
        items: orm.Mapped[list[Item]] = orm.relationship("Item", back_populates="department")

To join the tables for a filter to search by department name, we need to use the :class:`JoinMap <alchemical_storage.join.JoinMap>` class in conjunction with a :class:`FilterMap <alchemical_storage.filter.FilterMap>` class:

.. code-block:: python
    :caption: index_with_joins.py

    from alchemical_storage.storage.index import DatabaseIndex
    from .models import Item
    from .session import session # Assuming that the session is already
                                 # created in a separate file

    from alchemical_storage.join import JoinMap
    from alchemical_storage.filter import FilterMap

    joins = JoinMap(
        "base_package.models",
        ("department_name", ),
        "Item.department",
    )

    filters = FilterMap({
        "department_name": ("Department.name", ColumnElement.ilike),
    }, "base_package.models")

    index = DatabaseIndex(session, Item, Item.id, [joins, filters])

    items = index.get(
        department_name="%grocery%"
    )

This would (roughly) translate to this in SQL:

.. code-block:: sql
    :caption: SQL Query

    SELECT Items.id, Items.name, Items.price, Items.department_id, Items.deleted_at
    FROM Items
    JOIN Departments ON Items.department_id = Departments.id
    WHERE Departments.name ILIKE '%grocery%'



Putting It Together
~~~~~~~~~~~~~~~~~~~

Now that we have seen how to use filters, sorting, pagination, and joins, let's put it all together:

.. code-block:: python
    :caption: index_with_everything.py

    from alchemical_storage.storage.index import DatabaseIndex
    from .models import Item
    from .session import session # Assuming that the session is already
                                 # created in a separate file

    from alchemical_storage.filter import FilterMap, NullFilterMap, OrderByMap
    from alchemical_storage.pagination import PaginationMap
    from alchemical_storage.join import JoinMap

    import operator
    from sqlalchemy import ColumnElement

    filters = FilterMap({
        "name": ("Item.name", ColumnElement.ilike),
        "department_id": "Item.department_id",
        "price_gt": ("Item.price", operator.gt),
        "price_lt": ("Item.price", operator.lt),
        "department_name": ("Department.name", ColumnElement.ilike),
    }, "base_package.models")

    null_filters = NullFilterMap({
        "deleted": "Item.deleted_at",
    }, "base_package.models")

    order_by = OrderByMap({
        "name": "Item.name",
        "price": "Item.price",
    }, "base_package.models")

    pagination = PaginationMap({
        "pagination",
        "page_size",
        "first_item",
    })

    joins = JoinMap(
        "base_package.models",
        ("department_name", ),
        "Item.department",
    )

    index = DatabaseIndex(session, Item, Item.id, [
        # Note that the order of the filters, joins, etc. is important.
        joins,
        filters,
        null_filters,
        order_by,
        pagination,
    ])

    items = index.get(
        name="%apple%",
        department_id=1,
        price_gt=1.0,
        price_lt=10.0,
        deleted="null",
        order_by="name,-price",
        pagination={"page_size": 10, "first_item": 0},
        department_name="%grocery%"
    )

This would translate to (roughly) this in SQL:

.. code-block:: sql
    :caption: SQL Query

    SELECT Items.id, Items.name, Items.price, Items.department_id, Items.deleted_at
    FROM Items
    JOIN Departments ON Items.department_id = Departments.id
    WHERE Items.name ILIKE '%apple%'
    AND Items.department_id = 1
    AND Items.price > 1.0
    AND Items.price < 10.0
    AND Items.deleted_at IS NULL
    AND Departments.name ILIKE '%grocery%'
    ORDER BY Items.name ASC, Items.price DESC
    LIMIT 10 OFFSET 0

Statement Visitors
==================

All of the filters, sorting, paginatination, and joins above are implemented using the :class:`StatementVisitor <alchemical_storage.visitor.StatementVisitor>` class. They use the :meth:`StatementVisitor.visit_statement <alchemical_storage.filter.FilterMap.visit_statement>` that the calls the ``.where`` or ``.order_by`` methods of the SQLAlchemy query object.

Custom Statement Visitors
~~~~~~~~~~~~~~~~~~~~~~~~~

Custom :class:`StatementVisitor <alchemical_storage.visitor.StatementVisitor>` classes can be created by subclassing the :class:`StatementVisitor <alchemical_storage.visitor.StatementVisitor>` class and implementing the :meth:`StatementVisitor.visit_statement <alchemical_storage.visitor.StatementVisitor.visit_statement>` method. This method should return a SQLAlchemy statement object. It receives the SQLAlchemy query object and the keyword arguments passed to the :meth:`DatabaseIndex.get <alchemical_storage.storage.DatabaseIndex.get>` method.

.. code-block:: python
    :caption: custom_visitor.py

    from alchemical_storage.visitor import StatementVisitor

    class CustomVisitor(StatementVisitor):
        def visit_statement(self, statement, **kwargs):
            # Custom logic here
            return statement