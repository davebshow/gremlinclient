.. _using-aiohttp:

Using aiohttp
=============

Using the aiohttp client is easy::

    from gremlinclient.aiohttp_client import GraphDatabase
    >>> async def get_conn():
    ...     graph = GraphDatabase("ws://localhost:8182/")
    ...     conn = await graph.connect()
    ...     ...
    ...     await conn.close()  # await close


The main difference is that the aiohttp client :py:meth:`close` methods return futures.

For more info, see the :ref:`aiohttp Client docs<aiohttp-client>`
