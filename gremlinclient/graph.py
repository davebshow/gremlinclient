import socket
import sys
import textwrap

from tornado import concurrent
from tornado.httpclient import HTTPRequest, HTTPError
from tornado.ioloop import IOLoop
from tornado.websocket import websocket_connect

from gremlinclient.connection import Connection


PY_33 = sys.version_info >= (3, 3)
PY_35 = sys.version_info >= (3, 5)


class GraphDatabase(object):
    """This class generates connections to the Gremlin Server"""

    def __init__(self, url, timeout=None, username="", password="",
                 loop=None, validate_cert=False, future_class=None):
        self._url = url
        self._timeout = timeout
        self._username = username
        self._password = password
        self._loop = loop or IOLoop.current()
        self._validate_cert = validate_cert
        self._future_class = future_class or concurrent.Future

    def connect(self,
                session=None,
                force_close=False,
                force_release=False,
                pool=None):
        # Will provide option for user to build own request,
        # implement with SSL tests.
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
                gc = Connection(conn, self._timeout, self._username,
                                self._password, self._loop, self._validate_cert,
                                force_close, self._future_class, pool,
                                force_release, session)
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
        pass  # pragma: no cover

    if not PY_33:  # pragma: no cover
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

    if PY_33:  # pragma: no cover
        exec(textwrap.dedent("""
        def __iter__(self):
            return self.__await__()

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
            if isinstance(future, concurrent.Future):
                return (yield future)
            return (yield from future)
            """))

    # if PY_35:
    #     exec(textwrap.dedent("""
    #     def connection(self):
    #         '''Return async context manager for working with connection.
    #
    #         async with pool.get() as conn:
    #         '''
    #         return _AsyncGraphConnectionContextManager(self)"""))


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


# if PY_35:
#     # Need to implement/test
#     exec(textwrap.dedent("""
#     class _AsyncGraphConnectionContextManager:
#
#         __slots__ = ('_conn')
#
#         def __init__(self):
#             self._conn = None
#
#         async def __aenter__(self):
#             self._conn = await self.connect()
#             return self._conn
#
#         async def __aexit__(self, exc_type, exc_value, tb):
#             try:
#                 self._conn.close()
#             finally:
#                 self._conn = None"""))
