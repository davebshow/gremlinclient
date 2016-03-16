import collections
import sys
import textwrap

from logging import WARNING

from gremlinclient.graph import GraphDatabase
from gremlinclient.log import pool_logger


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
    :param loop: event loop
    :param bool validate_cert: validate ssl certificate. False by default
    :param class future_class: type of Future -
        :py:class:`asyncio.Future`, :py:class:`trollius.Future`, or
        :py:class:`tornado.concurrent.Future`
    """
    def __init__(self, graph, maxsize=256, loop=None, force_release=False,
                 log_level=WARNING, future_class=None):
        self._graph = graph
        self._maxsize = maxsize
        self._pool = collections.deque()
        self._waiters = collections.deque()
        self._acquired = set()
        self._acquiring = 0
        self._closed = False
        self._loop = loop
        self._force_release = force_release
        self._future_class = self._graph.future_class
        pool_logger.setLevel(log_level)

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
            while self._pool:
                conn = self._pool.popleft()
                if not conn.closed:
                    pool_logger.debug("Reusing connection: {}".format(conn))
                    future.set_result(conn)
                    self._acquired.add(conn)
                    break
                else:
                    pool_logger.debug(
                        "Discarded closed connection: {}".format(conn))
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
                    pool_logger.debug("Got new connection {}".format(conn))
                    self._acquired.add(conn)
                    future.set_result(conn)
                finally:
                    self._acquiring -= 1
            conn_future.add_done_callback(cb)
        else:
            pool_logger.debug(
                "Waiting for available conn on future: {}...".format(future))
            self._waiters.append(future)
        return future

    def release(self, conn):
        """
        Release a connection back to the pool.

        :param gremlinclient.connection.Connection: The connection to be
            released
        """
        future = self._future_class()
        if self.size <= self.maxsize:
            if conn.closed:
                # conn has been closed
                pool_logger.info(
                    "Released closed connection: {}".format(conn))
                self._acquired.remove(conn)
                conn = None
            elif self._waiters:
                waiter = self._waiters.popleft()
                waiter.set_result(conn)
                pool_logger.debug(
                    "Completeing future with connection: {}".format(conn))
            else:
                self._pool.append(conn)
                self._acquired.remove(conn)
            future.set_result(None)
        else:
            future_conn = conn.close()
            future_conn.add_done_callback(
                lambda f: future.set_result(f.result()))
        return future

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
        pool_logger.info(
            "Connection pool {} has been closed".format(self))

    def __enter__(self):
        raise RuntimeError(
                "context manager should use some variation of yield/yield from")

    def __exit__(self, *args):
        pass  # pragma: no cover
