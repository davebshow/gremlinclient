import collections

from tornado.concurrent import Future
from tornado.ioloop import IOLoop

from gremlinclient.factory import GremlinFactory
from gremlinclient.manager import _PoolConnectionContextManager


class GremlinPool(object):

    def __init__(self, url='ws://localhost:8182/', lang="gremlin-groovy",
                 processor="", timeout=None, username="", password="",
                 factory=None, maxsize=256, loop=None, force_release=False):
        self._maxsize = maxsize
        self._pool = collections.deque()
        self._waiters = collections.deque()
        self._acquired = set()
        self._acquiring = 0
        self._closed = False
        self._loop = loop or IOLoop.current()
        self._force_release = force_release
        # This may change depending on how other factories are passed
        self._factory = factory or GremlinFactory(url=url,
                                                  lang=lang,
                                                  processor=processor,
                                                  timeout=timeout,
                                                  username=username,
                                                  password=password)

    def connection(self):
        conn = self.acquire()
        return _PoolConnectionContextManager(self, conn)

    @property
    def freesize(self):
        return len(self._pool)

    @property
    def size(self):
        return len(self._acquired) + self._acquiring + self.freesize

    @property
    def maxsize(self):
        return self._maxsize

    @property
    def factory(self):
        return self._factory

    @property
    def pool(self):
        return self._pool

    @property
    def closed(self):
        return self._closed or self._factory is None

    def acquire(self):
        # maybe have max connection open time here
        future = Future()
        if self._pool:
            conn = self._pool.popleft()
            future.set_result(conn)
            self.acquired.add(conn)
        elif self.size < self.maxsize:
            self._acquiring += 1
            conn_future = self.factory.connect(
                force_release=self._force_release, pool=self)
            def cb(f):
                conn = f.result()
                self._acquiring -= 1
                self._acquired.add(conn)
                future.set_result(conn)
            self._loop.add_future(conn_future, cb)
        else:
            self._waiters.append(future)
        return future

    def release(self, conn):
        if self.size <= self.maxsize:
            if conn.closed:
                # conn has been closed
                self._acquired.remove(conn)
            elif self._waiters:
                waiter = self._waiters.popleft()
                waiter.set_result(conn)
            else:
                self._pool.append(conn)
                self._acquired.remove(conn)
        else:
            conn.close()
            self._acquired.remove(conn)

    def close(self):
        while self.pool:
            conn = self.pool.popleft()
            conn.close()
        while self._waiters:
            f = self._waiters.popleft()
            f.cancel()
        self._factory = None
        self._closed = True
