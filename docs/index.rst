.. gremlinclient documentation master file, created by
   sphinx-quickstart on Sat Jun 27 13:50:06 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=============
gremlinclient
=============

:py:mod:`gremlinclient` is an asynchronous Python client for the
`TinkerPop 3 Gremlin Server`_ based on the `Tornado`_ websocket client
implementation.

Releases
========
The latest release of :py:mod:`gremlinclient` is **0.1.9**.


Requirements
============

:py:mod:`gremlinclient` is built on `Tornado`_ and works with most versions of Python:

- Python 2.7+
- Tornado 4.1+

:py:mod:`gremlinclient` also supports `Asyncio`_ as follows:

- Python 3.4+, Python 3.3 and `Asyncio`_, or Python 2.7 and `Trollius`_

Already using `aiohttp`_? Checkout `aiogremlin`_.

Prefer to use the REST interface? Checkout `gremlinrestclient`_.

Installation
============
Install using pip::

    $ pip install gremlinclient

.. _getting-started:

Getting Started
===============

Submit a script to the Gremlin Server with Python 2.7 or 3.3+ using Tornado::

    >>> from tornado import gen
    >>> from tornado.ioloop import IOLoop
    >>> from gremlinclient import submit

    >>> loop = IOLoop.current()

    >>> @gen.coroutine
    ... def go():
    ...     resp = yield submit("ws://localhost:8182/", "1 + 1")
    ...     while True:
    ...         msg = yield resp.read()
    ...         if msg is None:
    ...             break
    ...         print(msg)
    >>> loop.run_sync(go)

    Message(status_code=200, data=[2], message=u'', metadata={})

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


Contents:

.. toctree::
   :maxdepth: 3

   usage
   modules


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _Tinkerpop 3 Gremlin Server: http://tinkerpop.incubator.apache.org/
.. _`Asyncio`: https://docs.python.org/3/library/asyncio.html
.. _`aiohttp`: http://aiohttp.readthedocs.org/en/stable/
.. _`Tornado`: http://www.tornadoweb.org/en/stable/
.. _Github: https://github.com/davebshow/gremlinclient/issues
.. _`aiogremlin`: http://aiogremlin.readthedocs.org/en/latest/
.. _`gremlinrestclient`: http://gremlinrestclient.readthedocs.org/en/latest/
.. _`Trollius`: http://trollius.readthedocs.org/
