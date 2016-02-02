# gremlinclient

[![Build Status](https://travis-ci.org/davebshow/gremlinclient.svg?branch=master)](https://travis-ci.org/davebshow/gremlinclient)
[![Coverage Status](https://coveralls.io/repos/github/davebshow/gremlinclient/badge.svg?branch=master)](https://coveralls.io/github/davebshow/gremlinclient?branch=master)


Multi-platform Python client for the TinkerPop 3 Gremlin Server - Tornado, Asyncio, Trollius

## [Official Documentation](http://gremlinclient.readthedocs.org/en/latest/)

## Requirements

* Python 2.7, 3.3, 3.4, 3.5
* Tornado 4.3 (earlier versions may also be supported)

## Getting Started

The following examples assume that you have the Gremlin Server running at port 8182.

###gremlinclient with Python 2.7 or 3.3 + using Tornado

```python
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
```

###gremlinclient with Python 2.7 using Trollius

```python
>>> import trollius
>>> from tornado.platform.asyncio import AsyncIOMainLoop
>>> from gremlinclient import submit

>>> AsyncIOMainLoop().install() # Use the asyncio event loop
>>> loop = trollius.get_event_loop()

>>> @trollius.coroutine
... def go():
...     fut = submit(
...         "ws://localhost:8182/", "1 + 1", future_class=trollius.Future)
...     resp = yield trollius.From(fut)
...     while True:
...         fut_msg = resp.read()
...         msg = yield trollius.From(fut_msg)
...         if msg is None:
...             break
...         print(msg)
>>> loop.run_until_complete(go())

Message(status_code=200, data=[2], message=u'', metadata={})
```

###gremlinclient with Python 3.3+ using Asyncio

```python
>>> import asyncio
>>> from tornado.platform.asyncio import AsyncIOMainLoop
>>> from gremlinclient import submit

>>> AsyncIOMainLoop().install() # Use the asyncio event loop
>>> loop = asyncio.get_event_loop()

>>> @asyncio.coroutine
... def go():
...     resp = yield from submit(
...         "ws://localhost:8182/", "1 + 1", future_class=asyncio.Future)
...     while True:
...         msg = yield from resp.read()
...         if msg is None:
...             break
...         print(msg)
>>> loop.run_until_complete(go())

Message(status_code=200, data=[2], message=u'', metadata={})
```

###gremlinclient with Python 3.5 using PEP492 async/await syntax

```python
>>> import asyncio
>>> from tornado.platform.asyncio import AsyncIOMainLoop
>>> from gremlinclient import submit

>>> AsyncIOMainLoop().install() # Use the asyncio event loop
>>> loop = asyncio.get_event_loop()

>>> async def go():
...     resp = await submit(
...         "ws://localhost:8182/", "1 + 1", future_class=asyncio.Future)
...     while True:
...         msg = await resp.read()
...         if msg is None:
...             break
...         print(msg)
>>> loop.run_until_complete(go())

Message(status_code=200, data=[2], message=u'', metadata={})
