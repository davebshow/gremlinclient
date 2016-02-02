Using :py:mod:`Gremlinclient`
=============================

Before you get started, make sure you have the `Gremlin Server`_ up and running.
All of the following examples use the `PEP 492`_ Python 3.5 async/await syntax, but
they can all be adjusted as shown in :ref:`Getting Started<getting-started>`.


Simple :py:mod:`API`
--------------------

Submit a script with :py:func:`gremlinclient.api.submit`::

    >>> async def do_submit():
    ...     resp = await submit(
    ...         "ws://localhost:8182/", "1 + 1",
    ...         future_class=asyncio.Future)
    ...     while True:
    ...         msg = await resp.read()
    ...         print(msg)
    ...         if msg is None:
    ...             break  # connection closes automatically

Get a database connection with :py:func:`gremlinclient.api.create_connection`::

    >>> async def get_conn():
    ...     conn = await create_connection("ws://localhost:8182/")
    ...     resp = conn.send(
    ...         "ws://localhost:8182/", "1 + 1",
    ...         future_class=asyncio.Future)
    ...     while True:
    ...         msg = await resp.read()
    ...         if msg is None:
    ...             break
    ...     conn.close()  # make sure conn is close when done


The :py:class:`GraphDatabase` object
------------------------------------

Get a database connection from :py:class:`gremlinclient.graph.GraphDatabase`::

    >>> async def get_conn():
    ...     graph = GraphDatabase("ws://localhost:8182/")
    ...     conn = await graph.connect()
    ...     ...
    ...     conn.close()

Get a database session connection from
:py:class:`gremlinclient.graph.GraphDatabase`::

    >>> async def get_conn():
      ...     graph = GraphDatabase("ws://localhost:8182/")
      ...     sess = await graph.session()  # session inherits from Connection
      ...     ...
      ...     sess.close()

Use :py:class:`gremlinclient.graph.GraphDatabase` as a context manager::

    >>> async def get_conn():
    ...     graph = GraphDatabase("ws://localhost:8182/")
    ...     with await graph as conn:  # conn is automatically closed on exit
    ...     ...

Note that `async with` is not implemented yet in :py:mod:`gremlinclient`

The :py:class:`Pool` object
---------------------------

Reuse websocket connections with :py:class:`gremlinclient.pool.Pool`::

    >>> async def get_conn():
    ...     pool = Pool("ws://localhost:8182/")
    ...     conn = await pool.acquire()
    ...     ...
    ...     pool.release(conn)

Automatically release connections to :py:class:`gremlinclient.pool.Pool` after read::

        >>> async def get_conn():
        ...     pool = Pool("ws://localhost:8182/", force_close=True)
        ...     conn = await pool.acquire()
        ...     resp = conn.send("1 + 1")
        ...     while True:
        ...         msg = await resp.read()
        ...         if msg is None:
        ...             break  # conn is automatically released to pool.
        ...         print(msg)

Use :py:class:`gremlinclient.pool.Pool` as a context manager::

    >>> async def get_conn():
    ...     graph = Pool("ws://localhost:8182/")
    ...     with await pool as conn:  # conn is automatically released on exit
    ...     ...


For more info, see the :ref:`Client Reference Guide<gremlinclient-client-reference>`


.. _Gremlin Server: http://tinkerpop.incubator.apache.org/
.. _PEP 492: https://www.python.org/dev/peps/pep-0492/
