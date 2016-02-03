import socket
import sys
import textwrap

try:
    import tornado
    from tornado.concurrent import Future
    from tornado.ioloop import IOLoop
except ImportError:
    print("Tornado not available.")

from gremlinclient.connection import Connection, Session
from gremlinclient.factory import TornadoFactory


PY_33 = sys.version_info >= (3, 3)
PY_35 = sys.version_info >= (3, 5)


class GraphDatabase(object):
    """This class generates connections to the Gremlin Server.

    :param str url: url for Gremlin Server.
    :param float timeout: timeout for establishing connection (optional).
        Values ``0`` or ``None`` mean no timeout
    :param str username: Username for SASL auth
    :param str password: Password for SASL auth
    :param loop: If param is ``None``, `tornado.ioloop.IOLoop.current`
        is used for getting default event loop (optional)
    :param bool validate_cert: validate ssl certificate. False by default
    :param class future_class: type of Future -
        :py:class:`asyncio.Future`, :py:class:`trollius.Future`, or
        :py:class:`tornado.concurrent.Future`
    """

    def __init__(self, url, factory=None, timeout=None, username="",
                 password="", loop=None, validate_cert=False,
                 future_class=None):
        self._url = url
        self._factory = factory or TornadoFactory
        self._timeout = timeout
        self._username = username
        self._password = password
        self._loop = loop or IOLoop.current()
        self._validate_cert = validate_cert
        self._future_class = future_class or Future

    def connect(self,
                session=None,
                force_close=False,
                force_release=False,
                pool=None):
        """
        Get a connection to the graph database.

        :param str session: Session id (optional). Typically a uuid
        :param bool force_close: force connection to close after read.
        :param bool force_release: If possible, force release to pool after
            read.
        :param gremlinclient.pool.Pool pool: Associated connection pool.

        :returns: :py:class:`gremlinclient.connection.Connection`
        """
        return self._connect(
            Connection, session, force_close, force_release, pool)

    def session(self,
                session=None,
                force_close=False,
                force_release=False,
                pool=None):
        """
        Get a session connection to the graph database.

        :param str session: Session id (optional). Typically a uuid
        :param bool force_close: force connection to close after read.
        :param bool force_release: If possible, force release to pool after
            read.
        :param gremlinclient.pool.Pool pool: Associated connection pool.

        :returns: :py:class:`gremlinclient.connection.Session`
        """
        return self._connect(
            Session, session, force_close, force_release, pool)

    def _connect(self,
                 conn_type,
                 session,
                 force_close,
                 force_release,
                 pool):
        # Will provide option for user to build own request,
        # implement with SSL tests.
        future = self._future_class()
        future_conn = self._factory.ws_connect(
            self._url, validate_cert=self._validate_cert)

        def get_conn(f):
            try:
                conn = f.result()
            except Exception as e:
                future.set_exception(e)
            else:
                gc = conn_type(conn, self._timeout, self._username,
                               self._password, self._loop,
                               self._validate_cert, force_close,
                               self._future_class, pool, force_release,
                               session)
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
