.. _tornado-asyncio:

Tornado/Asyncio Integration
===========================

Submit a script to the Gremlin Server with Python 3.3+ and Asyncio::

    >>> import asyncio
    >>> from tornado.platform.asyncio import AsyncIOMainLoop
    >>> from gremlinclient import submit

    >>> AsyncIOMainLoop().install() # Use the asyncio event loop
    >>> loop = asyncio.get_event_loop()

    >>> @asyncio.coroutine
    ... def go():
    ...     resp = yield from submit(
    ...         "ws://localhost:8182/", "1 + 1",
    ...         future_class=asyncio.Future)
    ...     while True:
    ...         msg = yield from resp.read()
    ...         if msg is None:
    ...             break
    ...         print(msg)
    >>> loop.run_until_complete(go())

    Message(status_code=200, data=[2], message=u'', metadata={})


Submit a script with Python 3.5 using PEP492 async/await syntax (Asyncio)::

    >>> import asyncio
    >>> from tornado.platform.asyncio import AsyncIOMainLoop
    >>> from gremlinclient import submit

    >>> AsyncIOMainLoop().install() # Use the asyncio event loop
    >>> loop = asyncio.get_event_loop()

    >>> async def go():
    ...     resp = await submit(
    ...         "ws://localhost:8182/", "1 + 1",
    ...         future_class=asyncio.Future)
    ...     while True:
    ...         msg = await resp.read()
    ...         if msg is None:
    ...             break
    ...         print(msg)
    >>> loop.run_until_complete(go())

    Message(status_code=200, data=[2], message=u'', metadata={})

Submit a script to the Gremlin Server with Python 2.7 using Trollius::

    >>> import trollius
    >>> from tornado.platform.asyncio import AsyncIOMainLoop
    >>> from gremlinclient import submit

    >>> AsyncIOMainLoop().install() # Use the asyncio event loop
    >>> loop = trollius.get_event_loop()

    >>> @trollius.coroutine
    ... def go():
    ...     fut = submit(
    ...         "ws://localhost:8182/", "1 + 1",
    ...         future_class=trollius.Future)
    ...     resp = yield trollius.From(fut)
    ...     while True:
    ...         fut_msg = resp.read()
    ...         msg = yield trollius.From(fut_msg)
    ...         if msg is None:
    ...             break
    ...         print(msg)
    >>> loop.run_until_complete(go())

    Message(status_code=200, data=[2], message=u'', metadata={})
