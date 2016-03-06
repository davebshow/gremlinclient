from __future__ import absolute_import
from logging import WARNING
import socket

from tornado import concurrent
from tornado.httpclient import HTTPRequest, HTTPError
from tornado.websocket import websocket_connect

from gremlinclient.api import _submit, _create_connection
from gremlinclient.graph import GraphDatabase
from gremlinclient.log import pool_logger
from gremlinclient.pool import Pool
from gremlinclient.response import Response


class Response(Response):
    """
    Wrapper for Tornado websocket client connection.

    :param tornado.websocket.WebSocketClientConnection conn: The websocket
        connection
    """

    @property
    def conn(self):
        """
        :returns: Underlying connection.
        """
        return self._conn

    @property
    def closed(self):
        """
        :returns: Connection protocol. None if conn is closed
        """
        return self._conn.protocol is None

    def close(self):
        """
        Close underlying client connection
        """
        self._conn.close()
        f = self._future_class()
        f.set_result(None)
        return f

    def send(self, msg, binary=True):
        """
        Send a message

        :param msg: The message to be sent.
        :param bool binary: Whether or not the message is encoded as bytes.
        """
        self._conn.write_message(msg, binary=binary)

    def receive(self, callback=None):
        """
        Read a message off the websocket.
        :param callback: To be called on message read.

        :returns: :py:class:`tornado.concurrent.Future`
        """
        return self._conn.read_message(callback=callback)


class GraphDatabase(GraphDatabase):

    def __init__(self, url, timeout=None, username="", password="",
                 loop=None, validate_cert=False, future_class=None):
        if future_class is None:
            future_class = concurrent.Future
        super(GraphDatabase, self).__init__(
            url, timeout=timeout, username=username, password=password,
            loop=loop, validate_cert=validate_cert,
            future_class=future_class)

    def _connect(self,
                 conn_type,
                 session,
                 force_close,
                 force_release,
                 pool):
        future = self._future_class()
        if not isinstance(self._url, HTTPRequest):
            request = HTTPRequest(self._url, validate_cert=self._validate_cert)
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
            except Exception as e:
                future.set_exception(e)
            else:
                resp = Response(conn, self._future_class, self._loop)
                gc = conn_type(resp, self._future_class, self._timeout,
                               self._username, self._password, self._loop,
                               self._validate_cert, force_close, pool,
                               force_release, session)
                future.set_result(gc)
        future_conn.add_done_callback(get_conn)
        return future



class Pool(Pool):
    def __init__(self, url, timeout=None, username="", password="",
                 maxsize=256, loop=None, force_release=False,
                 log_level=WARNING, future_class=None):
        super(Pool, self).__init__(url, timeout=timeout, username=username,
                         password=password, graph_class=GraphDatabase,
                         maxsize=maxsize, loop=loop, log_level=log_level,
                         force_release=force_release,
                         future_class=future_class)


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
        :py:class:`asyncio.Future`, :py:class:`trollius.Future`, or
        :py:class:`tornado.concurrent.Future`

    :returns: :py:class:`gremlinclient.connection.Stream` object:
    """
    return _submit(url, gremlin, GraphDatabase, bindings=None, lang=lang,
                   aliases=aliases, op=op, processor=processor, graph=None,
                   timeout=timeout, session=session, loop=loop,
                   username=username, password=password,
                   validate_cert=validate_cert, future_class=future_class)


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
        :py:class:`asyncio.Future`, :py:class:`trollius.Future`, or
        :py:class:`tornado.concurrent.Future`
    :param str session: Session id (optional). Typically a uuid
    :returns: :py:class:`gremlinclient.connection.Connection` object:
    """

    return _create_connection(url, GraphDatabase, timeout=timeout,
                              username=username, password=password,
                              loop=loop, validate_cert=validate_cert,
                              session=session, force_close=force_close,
                              future_class=future_class)
