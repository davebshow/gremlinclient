.. _basic-usage:

Using :py:mod:`gremlinclient`
=============================

Before you get started, make sure you have the `Gremlin Server`_ up and running.
All of the following examples use the Tornado client with `PEP 492`_
Python 3.5 async/await syntax, but they can all be adjusted as shown in
the :ref:`Using aiohttp<using-aiohttp>` and
:ref:`Tornado Asyncio Integration<tornado-asyncio>` sections.


Simple :py:mod:`API`
--------------------

Submit a script with :py:func:`submit<gremlinclient.tornado_client.client.submit>`::

    >>> async def do_submit():
    ...     resp = await submit(
    ...         "ws://localhost:8182/", "1 + 1")
    ...     while True:
    ...         msg = await resp.read()
    ...         if msg is None:
    ...             break  # connection closes automatically
    ...         print(msg)

Get a database connection with :py:func:`create_connection<gremlinclient.tornado_client.client.create_connection>`::

    >>> async def get_conn():
    ...     conn = await create_connection("ws://localhost:8182/")
    ...     resp = conn.send(
    ...         "ws://localhost:8182/", "1 + 1")
    ...     while True:
    ...         msg = await resp.read()
    ...         if msg is None:
    ...             break
    ...     conn.close()  # make sure conn is closed when done


The :py:class:`GraphDatabase` object
------------------------------------

Get a database connection from :py:class:`GraphDatabase<gremlinclient.tornado_client.client.GraphDatabase>`::

    >>> async def get_conn():
    ...     graph = GraphDatabase("ws://localhost:8182/")
    ...     conn = await graph.connect()
    ...     ...
    ...     conn.close()

Get a database session connection from
:py:class:`GraphDatabase<gremlinclient.tornado_client.client.GraphDatabase>`::

    >>> async def get_conn():
      ...     graph = GraphDatabase("ws://localhost:8182/")
      ...     sess = await graph.session()  # session inherits from Connection
      ...     ...
      ...     sess.close()


The :py:class:`Pool` object
---------------------------

Reuse websocket connections with :py:class:`Pool<gremlinclient.tornado_client.client.Pool>`::

    >>> async def get_conn():
    ...     pool = Pool("ws://localhost:8182/")
    ...     conn = await pool.acquire()
    ...     ...
    ...     pool.release(conn)
    ...     pool.close()  # Close all released conns

Automatically release connections to :py:class:`Pool<gremlinclient.tornado_client.client.Pool>` after read::

        >>> async def get_conn():
        ...     pool = Pool("ws://localhost:8182/", force_release=True)
        ...     conn = await pool.acquire()
        ...     resp = conn.send("1 + 1")
        ...     while True:
        ...         msg = await resp.read()
        ...         if msg is None:
        ...             break  # conn is automatically released to pool.
        ...      pool.close()


For more info, see the :ref:`Tornado Client docs<tornado-client>`


.. _Gremlin Server: http://tinkerpop.incubator.apache.org/
.. _PEP 492: https://www.python.org/dev/peps/pep-0492/
