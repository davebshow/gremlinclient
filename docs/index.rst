.. gremlinclient documentation master file, created by
   sphinx-quickstart on Sat Jun 27 13:50:06 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=============
gremlinclient
=============

:py:mod:`gremlinclient` is an asynchronous multi-client Python driver for the
`TinkerPop 3`_ `Gremlin Server`_. By default, it uses the `Tornado`_ websocket client
implementation to communicate with the server, but it also supports `aiohttp`_ for a
pure `Asyncio`_ implementation--support for `Pulsar`_ and `requests-futures`_ coming soon.

Releases
========
The latest release of :py:mod:`gremlinclient` is **0.2.3**.

Requirements
============

:py:mod:`gremlinclient` with `Tornado`_ requires Python 2.7+. That said, there are a variety of
client/library combinations that work with different versions of Python.

Tornado

- Python 2.7+

Tornado w/`Asyncio`_

- Python 3.3+

Tornado w/`Trollius`_

- Python 2.7

`aiohttp`_

- Python 3.4+

Installation
============
Install using pip::

    $ pip install gremlinclient

.. _getting-started:

Getting Started
===============

Submit a script to the `Gremlin Server`_ with Python 2.7 or 3.3+ using `Tornado`_::

    >>> from tornado import gen
    >>> from tornado.ioloop import IOLoop
    >>> from gremlinclient.tornado_client import submit

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


Contents:

.. toctree::
   :maxdepth: 3

   usage
   using_aiohttp
   tornado_asyncio_integration
   ssl
   modules


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _Tinkerpop 3: http://tinkerpop.incubator.apache.org/
.. _Gremlin Server: http://tinkerpop.apache.org/docs/3.1.1-incubating/reference/#gremlin-server
.. _`Asyncio`: https://docs.python.org/3/library/asyncio.html
.. _`aiohttp`: http://aiohttp.readthedocs.org/en/stable/
.. _`Tornado`: http://www.tornadoweb.org/en/stable/
.. _Github: https://github.com/davebshow/gremlinclient/issues
.. _`aiogremlin`: http://aiogremlin.readthedocs.org/en/latest/
.. _`gremlinrestclient`: http://gremlinrestclient.readthedocs.org/en/latest/
.. _`Trollius`: http://trollius.readthedocs.org/
.. _`requests-futures`: https://pypi.python.org/pypi/requests-futures
.. _`Pulsar`: https://pythonhosted.org/pulsar/
