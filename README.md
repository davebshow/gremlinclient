# gremlinclient

[![Build Status](https://travis-ci.org/davebshow/gremlinclient.svg?branch=master)](https://travis-ci.org/davebshow/gremlinclient)
[![Coverage Status](https://coveralls.io/repos/github/davebshow/gremlinclient/badge.svg?branch=master)](https://coveralls.io/github/davebshow/gremlinclient?branch=master)


Multi-platform Python client for the TinkerPop 3 Gremlin Server - Tornado, Asyncio, Trollius

## [Official Documentation](http://gremlinclient.readthedocs.org/en/latest/)

Submit a script to the Gremlin Server with Python 2.7 or 3.3+ using Tornado

```python
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
