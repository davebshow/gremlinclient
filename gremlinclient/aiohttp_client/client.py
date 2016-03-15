import asyncio
import functools
import sys

from logging import WARNING

try:
    import aiohttp
except ImportError:
    raise ImportError(
        "Please install aiohttp to use the gremlinclient.aiohttp module")

from gremlinclient.api import _submit, _create_connection
from gremlinclient.connection import Connection, Session
from gremlinclient.graph import GraphDatabase
from gremlinclient.log import pool_logger
from gremlinclient.pool import Pool
from gremlinclient.response import Response


PY_35 = sys.version_info >= (3, 5)


class Response(Response):
    """
    Wrapper for aiohttp websocket client connection.

    :param aiohttp.ClientWebSocketResponse conn: The websocket
        connection
    """

    @property
    def closed(self):
        """
        :returns: bool. True if conn is closed
        """
        return self._conn.closed

    def close(self):
        """
        Close underlying client connection
        :returns: :py:class:`asyncio.Future`
        """
        return asyncio.async(self._conn.close(), loop=self._loop)

    def send(self, msg, binary=True):
        """
        Send a message

        :param msg: The message to be sent.
        :param bool binary: Whether or not the message is encoded as bytes.
        """
        if binary:
            self._conn.send_bytes(msg)
        else:
            self._conn.send_string(msg)

    def receive(self, callback=None):
        """
        Read a message off the websocket.
        :param callback: To be called on message read.

        :returns: :py:class:`asyncio.Future`
        """
        future = self._future_class()
        future_read = asyncio.async(self._conn.receive(), loop=self._loop)

        def on_receive(f):
            try:
                msg = f.result()
            except Exception as e:
                future.set_exception(e)
            else:
                if msg.tp == aiohttp.MsgType.binary:
                    future.set_result(msg.data)
                elif msg.tp == aiohttp.MsgType.text:
                    self.parser.feed_data(msg.data.encode("utf-8"))
                else:
                    if msg.tp == aiohttp.MsgType.close:
                        future_close = asyncio.async(ws.close())

                        def on_close(f):
                            try:
                                f.result()
                            except Exception as e:
                                future.set_exception(e)
                            else:
                                future.set_result(None)

                        future_close.add_done_callback(on_close)

                    elif msg.tp == aiohttp.MsgType.error:
                        future.set_exception(msg.data)
                    elif msg.tp == aiohttp.MsgType.closed:
                        pass

        future_read.add_done_callback(on_receive)
        future.add_done_callback(callback)
        return future


class GraphDatabase(GraphDatabase):
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

    def __init__(self, url, timeout=None, username="", password="",
                 loop=None, validate_cert=False, future_class=None):
        future_class = functools.partial(asyncio.Future, loop=loop)
        super().__init__(url, timeout=timeout, username=username,
                         password=password, loop=loop,
                         validate_cert=validate_cert, future_class=future_class)

    def _connect(self,
                 conn_type,
                 session,
                 force_close,
                 force_release,
                 pool):
        connector = aiohttp.TCPConnector(force_close=force_close,
                                         loop=self._loop,
                                         verify_ssl=self._validate_cert)
        future = self._future_class()
        ws = aiohttp.ws_connect(self._url, connector=connector, loop=self._loop)
        if self._timeout:
            future_conn = asyncio.wait_for(ws, self._timeout, loop=self._loop)
        else:
            future_conn = asyncio.async(ws, loop=self._loop)

        def on_connect(f):
            try:
                conn = f.result()
            # Need to figure out some errors
            except Exception as e:
                future.set_exception(e)
            else:
                resp = Response(conn, self._future_class, loop=self._loop)
                gc = conn_type(resp, self._future_class, self._timeout,
                               self._username, self._password, self._loop,
                               self._validate_cert, force_close, pool,
                               force_release, session)
                future.set_result(gc)

        future_conn.add_done_callback(on_connect)

        return future


class Pool(Pool):
    """
    Pool of :py:class:`gremlinclient.connection.Connection` objects.

    :param str url: url for Gremlin Server.
    :param float timeout: timeout for establishing connection (optional).
        Values ``0`` or ``None`` mean no timeout
    :param str username: Username for SASL auth
    :param str password: Password for SASL auth
    :param gremlinclient.aiohttp_client.client.GraphDatabase graph: The graph
        instance used to create connections
    :param int maxsize: Maximum number of connections.
    :param loop: event loop
    :param bool validate_cert: validate ssl certificate. False by default
    :param class future_class: type of Future -
        :py:class:`asyncio.Future` by default
    """
    def __init__(self, url, timeout=None, username="", password="",
                 maxsize=256, loop=None, log_level=WARNING,
                 future_class=None, force_release=False):
        super().__init__(url, timeout=timeout, username=username,
                         password=password, graph_class=GraphDatabase,
                         maxsize=maxsize, loop=loop, log_level=log_level,
                         force_release=force_release)

    def close(self):
        """
        Close pool.
        :returns: :py:class:`asyncio.Future`
        """
        return asyncio.async(self._close(), loop=self._loop)

    @asyncio.coroutine
    def _close(self):
        to_close = []
        while self.pool:
            conn = self.pool.popleft()
            to_close.append(conn.close())
        yield from asyncio.gather(*to_close, loop=self._loop)
        while self._waiters:
            f = self._waiters.popleft()
            f.cancel()
        self._graph = None
        self._closed = True
        pool_logger.info(
            "Connection pool {} has been closed".format(self))

    def release(self, conn):
        """
        Release a connection back to the pool.

        :param gremlinclient.connection.Connection: The connection to be
            released
        :returns: :py:class:`asyncio.Future`
        """
        return asyncio.async(self._release(conn), loop=self._loop)

    @asyncio.coroutine
    def _release(self, conn):
        result = super().release(conn)
        if result is None:
            return
        return result


def submit(url,
           gremlin,
           bindings=None,
           lang="gremlin-groovy",
           aliases=None,
           op="eval",
           processor="",
           timeout=None,
           session=None,
           loop=None,
           username="",
           password="",
           validate_cert=False,
           future_class=None):
    """
    Submit a script to the Gremlin Server.

    :param str url: url for Gremlin Server.
    :param str gremlin: Gremlin script to submit to server.
    :param dict bindings: A mapping of bindings for Gremlin script.
    :param str lang: Language of scripts submitted to the server.
        "gremlin-groovy" by default
    :param dict aliases: Rebind ``Graph`` and ``TraversalSource``
        objects to different variable names in the current request
    :param str op: Gremlin Server op argument. "eval" by default.
    :param str processor: Gremlin Server processor argument. "" by default.
    :param float timeout: timeout for establishing connection (optional).
        Values ``0`` or ``None`` mean no timeout
    :param str session: Session id (optional). Typically a uuid
    :param loop: If param is ``None``, :py:meth:`tornado.ioloop.IOLoop.current`
        is used for getting default event loop (optional)
    :param str username: Username for SASL auth
    :param str password: Password for SASL auth
    :param bool validate_cert: validate ssl certificate. False by default
    :param class future_class: type of Future -
        :py:class:`asyncio.Future` by default

    :returns: :py:class:`gremlinclient.connection.Stream` object:
    """
    return _submit(url, gremlin, GraphDatabase, bindings=None, lang=lang,
                   aliases=aliases, op=op, processor=processor, graph=None,
                   timeout=timeout, session=session, loop=loop,
                   username=username, password=password,
                   validate_cert=validate_cert, future_class=None)


def create_connection(url, timeout=None, username="", password="",
                       loop=None, validate_cert=False, session=None,
                       force_close=False, future_class=None):
    """
    Get a database connection from the Gremlin Server.

    :param str url: url for Gremlin Server.
    :param float timeout: timeout for establishing connection (optional).
        Values ``0`` or ``None`` mean no timeout
    :param str username: Username for SASL auth
    :param str password: Password for SASL auth
    :param loop: If param is ``None``, :py:meth:`tornado.ioloop.IOLoop.current`
        is used for getting default event loop (optional)
    :param bool validate_cert: validate ssl certificate. False by default
    :param bool force_close: force connection to close after read.
    :param class future_class: type of Future -
        :py:class:`asyncio.Future` by default
    :param str session: Session id (optional). Typically a uuid
    :returns: :py:class:`gremlinclient.connection.Connection` object:
    """

    return _create_connection(url, GraphDatabase, timeout=timeout,
                              username=username, password=password,
                              loop=loop, validate_cert=validate_cert,
                              session=session, force_close=force_close,
                              future_class=future_class)
