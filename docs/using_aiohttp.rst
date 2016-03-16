.. _using-aiohttp:

Using aiohttp
=============

:py:mod:`aiohttp` is not installed with :py:mod:`gremlinclient` by default. Use pip
to install it::

    $ pip install aiohttp

If you aren't using tornado, go ahead and uninstall it::

    $ pip uninstall tornado

Using the :py:mod:`aiohttp client<gremlinclient.aiohttp_client>` is easy,
it provides the exact same objects and API as the
:py:mod:`Tornado client<gremlinclient.tornado_client>` with one small exception:
the :py:meth:`close` methods return :py:class:`asyncio.Future` that must be yielded
from or awaited. For example::

    >>> from gremlinclient.aiohttp_client import GraphDatabase
    >>> async def get_conn():
    ...     graph = GraphDatabase("ws://localhost:8182/")
    ...     conn = await graph.connect()
    ...     ...
    ...     await conn.close()  # await close

Or if you are using a :py:class:`Pool<gremlinclient.aiohttp_client.client.Pool>`::

    >>> from gremlinclient.aiohttp_client import Pool
    >>> async def use_pool():
    ...     pool = Pool("ws://localhost:8182/")
    ...     conn = yield from pool.acquire()
    ...     ...
    ...     await pool.release(conn)
    ...     await pool.close()


For more info, see the :ref:`aiohttp client docs<aiohttp-client>`
