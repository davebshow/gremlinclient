import collections
import sys
import textwrap

try:
    import tornado
    from tornado.concurrent import Future
    from tornado.ioloop import IOLoop
except:
    print("Tornado not available.")

from gremlinclient.graph import GraphDatabase


PY_33 = sys.version_info >= (3, 3)
PY_35 = sys.version_info >= (3, 5)


class Pool(object):
    """
    Pool of :py:class:`gremlinclient.connection.Connection` objects.

    :param str url: url for Gremlin Server.
    :param float timeout: timeout for establishing connection (optional).
        Values ``0`` or ``None`` mean no timeout
    :param str username: Username for SASL auth
    :param str password: Password for SASL auth
    :param gremlinclient.graph.GraphDatabase graph: The graph instances
        used to create connections
    :param int maxsize: Maximum number of connections.
    :param loop: If param is ``None``, `tornado.ioloop.IOLoop.current`
        is used for getting default event loop (optional)
    :param bool validate_cert: validate ssl certificate. False by default
    :param class future_class: type of Future -
        :py:class:`asyncio.Future`, :py:class:`trollius.Future`, or
        :py:class:`tornado.concurrent.Future`
    """
    def __init__(self, url, timeout=None,
                 username="", password="", graph=None, maxsize=256, loop=None,
                 force_release=False, future_class=None):
        self._maxsize = maxsize
        self._pool = collections.deque()
        self._waiters = collections.deque()
        self._acquired = set()
        self._acquiring = 0
        self._closed = False
        self._loop = loop or IOLoop.current()
        self._force_release = force_release
        self._future_class = future_class or Future
        # This may change depending on how other factories are passed
        self._graph = graph or GraphDatabase(url,
                                             timeout=timeout,
                                             username=username,
                                             password=password,
                                             future_class=future_class)

    @property
    def freesize(self):
        """
        Number of free connections

        :returns: int
        """
        return len(self._pool)

    @property
    def size(self):
        """
        Total number of connections

        :returns: int
        """
        return len(self._acquired) + self._acquiring + self.freesize

    @property
    def maxsize(self):
        """
        Maximum number of connections

        :returns: in
        """
        return self._maxsize

    @property
    def graph(self):
        """
        Associated graph instance used for creating connections

        :returns: :py:class:`gremlinclient.graph.GraphDatabase`
        """
        return self._graph

    @property
    def pool(self):
        """
        Object that stores unused connections

        :returns: :py:class:`collections.deque`
        """
        return self._pool

    @property
    def closed(self):
        """
        Check if pool has been closed

        :returns: bool
        """
        return self._closed or self._graph is None

    def acquire(self):
        # maybe have max connection open time here
        """
        Acquire a connection from the Pool

        :returns: Future -
            :py:class:`asyncio.Future`, :py:class:`trollius.Future`, or
            :py:class:`tornado.concurrent.Future`
        """
        future = self._future_class()
        if self._pool:
            conn = self._pool.popleft()
            future.set_result(conn)
            self._acquired.add(conn)
        elif self.size < self.maxsize:
            self._acquiring += 1
            conn_future = self.graph.connect(
                force_release=self._force_release, pool=self)
            def cb(f):
                try:
                    conn = f.result()
                except Exception as e:
                    future.set_exception(e)
                else:
                    self._acquired.add(conn)
                    future.set_result(conn)
                finally:
                    self._acquiring -= 1
            conn_future.add_done_callback(cb)
        else:
            self._waiters.append(future)
        return future

    def release(self, conn):
        """
        Release a connection back to the pool.

        :param gremlinclient.connection.Connection: The connection to be
            released
        """
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
        """
        Close pool
        """
        while self.pool:
            conn = self.pool.popleft()
            conn.close()
        while self._waiters:
            f = self._waiters.popleft()
            f.cancel()
        self._graph = None
        self._closed = True

# The follwoing is inspired by:
# https://github.com/aio-libs/aioredis/blob/master/aioredis/pool.py
# and
# http://www.tornadoweb.org/en/stable/_modules/tornado/concurrent.html#Future
    def __enter__(self):
        raise RuntimeError(
                "context manager should use some variation of yield/yield from")

    def __exit__(self, *args):
        pass  # pragma: no cover

    if not PY_33:  # pragma: no cover
        def __await__(self):
            future = self._future_class()
            future_conn = self.acquire()

            def on_connect(f):
                try:
                    conn = f.result()
                except Exception as e:
                    future.set_exception(e)
                else:
                    future.set_result(
                        _PoolConnectionContextManager(self, conn))

            future_conn.add_done_callback(on_connect)
            result = yield future
            # StopIteration doesn't take args before py33,
            # but Cython recognizes the args tuple.
            e = StopIteration()
            e.args = (result,)
            raise e

    if PY_33:  # pragma: no cover
        exec(textwrap.dedent("""

        def __iter__(self):
            future = self._future_class()
            future_conn = self.acquire()

            def on_connect(f):
                try:
                    conn = f.result()
                except Exception as e:
                    future.set_exception(e)
                else:
                    future.set_result(
                        _PoolConnectionContextManager(self, conn))

            future_conn.add_done_callback(on_connect)
            if isinstance(future, tornado.concurrent.Future):
                return (yield future)
            return (yield from future)

        __await__ = __iter__"""))

    # if PY_35:
    #     exec(textwrap.dedent("""
    #     def connection(self):
    #         '''Return async context manager for working with connection.
    #
    #         async with pool.get() as conn:
    #         '''
    #         return _AsyncConnectionContextManager(self)"""))


class _PoolConnectionContextManager(object):

    __slots__ = ('_pool', '_conn')

    def __init__(self, pool, conn):
        self._pool = pool
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, exc_type, exc_value, tb):
        try:
            self._pool.release(self._conn)
        finally:
            self._pool = None
            self._conn = None


# if PY_35:
#     exec(textwrap.dedent("""
#     class _AsyncPoolConnectionContextManager:
#
#         __slots__ = ('_pool', '_conn')
#
#         def __init__(self, pool):
#             self._pool = pool
#             self._conn = None
#
#         async def __aenter__(self):
#             self._conn = await self._pool.acquire()
#             return self._conn
#
#         async def __aexit__(self, exc_type, exc_value, tb):
#             try:
#                 self._pool.release(self._conn)
#             finally:
#                 self._pool = None
#                 self._conn = None"""))
