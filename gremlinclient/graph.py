import socket
import sys
import textwrap

from tornado import concurrent
from tornado.httpclient import HTTPRequest, HTTPError
from tornado.ioloop import IOLoop
from tornado.websocket import websocket_connect

from gremlinclient.base import AbstractBaseGraph
from gremlinclient.connection import GremlinConnection


PY_33 = sys.version_info >= (3, 3)
PY_35 = sys.version_info >= (3, 5)


class GraphDatabase(AbstractBaseGraph):
    """This class generates connections to the Gremlin Server"""

    def __init__(self, url='ws://localhost:8182/', lang="gremlin-groovy",
                 processor="", timeout=None, username="", password="",
                 loop=None, validate_cert=False, future_class=None):
        self._url = url
        self._lang = lang
        self._processor = processor
        self._timeout = timeout
        self._username = username
        self._password = password
        self._loop = loop or IOLoop.current()
        self._validate_cert = validate_cert
        self._future_class = future_class or concurrent.Future

    def connect(self, force_close=False, force_release=False, pool=None):
        request = HTTPRequest(self._url, validate_cert=self._validate_cert)
        future = self._future_class()
        future_conn = websocket_connect(request)

        def get_conn(f):
            try:
                conn = f.result()
            except socket.error:
                future.set_exception(
                    RuntimeError("Could not connect to server."))
            except socket.gaierror:
                future.set_exception(
                    RuntimeError("Could not connect to server."))
            except HTTPError as e:
                future.set_exception(e)
            else:
                gc = GremlinConnection(conn, self._lang, self._processor,
                                       self._timeout, self._username,
                                       self._password, force_close=force_close,
                                       force_release=force_release, pool=pool,
                                       future_class=self._future_class)
                future.set_result(gc)
        future_conn.add_done_callback(get_conn)
        return future

# The follwoing is inspired by:
# https://github.com/aio-libs/aioredis/blob/master/aioredis/pool.py
# and
# http://www.tornadoweb.org/en/stable/_modules/tornado/concurrent.html#Future
    def __enter__(self):
        raise RuntimeError(
            "context manager should use some variation of yield/yield from")

    def __exit__(self, *args):
        pass

    if not PY_33:
        def __await__(self):
            future = self._future_class()
            future_conn = self.connect()

            def on_connect(f):
                try:
                    conn = f.result()
                except Exception as e:
                    future.set_exception(e)
                else:
                    future.set_result(
                        _GraphConnectionContextManager(conn))

            future_conn.add_done_callback(on_connect)
            result = yield future
            # StopIteration doesn't take args before py33,
            # but Cython recognizes the args tuple.
            e = StopIteration()
            e.args = (result,)
            raise e

    if PY_33:
        exec(textwrap.dedent("""
        def __await__(self):
            future = self._future_class()
            future_conn = self.connect()

            def on_connect(f):
                try:
                    conn = f.result()
                except Exception as e:
                    future.set_exception(e)
                else:
                    future.set_result(
                        _GraphConnectionContextManager(conn))

            future_conn.add_done_callback(on_connect)
            return (yield future)"""))

    if PY_35:
        exec(textwrap.dedent("""

        def connection(self):
            '''Return async context manager for working with connection.

            async with pool.get() as conn:
            '''
            return _AsyncConnectionContextManager(self)"""))


class _GraphConnectionContextManager(object):

    __slots__ = ('_conn')

    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, exc_type, exc_value, tb):
        try:
            self._conn.close()
        finally:
            self._conn = None


if PY_35:
    # Need to implement/test
    exec(textwrap.dedent("""
    import asyncio
    class _AsyncGraphConnectionContextManager:

        __slots__ = ('_conn')

        def __init__(self, conn):
            self._conn = None

        @asyncio.coroutine
        def __aenter__(self):
            return self._conn

        @asyncio.coroutine
        def __aexit__(self, exc_type, exc_value, tb):
            try:
                self._conn.close()
            finally:
                self._conn = None"""))
