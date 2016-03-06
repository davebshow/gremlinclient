import base64
import collections
import uuid
try:
    import ujson as json
except ImportError:
    import json


Message = collections.namedtuple(
    "Message",
    ["status_code", "data", "message", "metadata"])


class Connection(object):
    """This class encapsulates a connection to the Gremlin Server.
    Don't directly create `Connection` instances. Use
    :py:meth:`gremlinclient.graph.GraphDatabase.connect` or
    :py:func:`gremlinclient.api.create_connection` instead.

    :param tornado.websocket.WebSocketClientConnection conn: client
        websocket connection.
    :param float timeout: timeout for establishing connection (optional).
        Values ``0`` or ``None`` mean no timeout
    :param str username: Username for SASL auth
    :param str password: Password for SASL auth
    :param loop: If param is ``None``, `tornado.ioloop.IOLoop.current`
        is used for getting default event loop (optional)
    :param bool validate_cert: validate ssl certificate. False by default
    :param bool force_close: force connection to close after read.
    :param class future_class: type of Future -
        :py:class:`asyncio.Future`, :py:class:`trollius.Future`, or
        :py:class:`tornado.concurrent.Future`
    :param gremlinclient.pool.Pool pool: Connection pool. None by default
    :param bool force_release: If possible, force release to pool after read.
    :param str session: Session id (optional). Typically a uuid
    """
    def __init__(self, conn, future_class, timeout=None, username="",
                 password="", loop=None, validate_cert=False,
                 force_close=False, pool=None, force_release=False,
                 session=None):
        self._conn = conn
        self._future_class = future_class
        self._closed = False
        self._session = session
        self._timeout = timeout
        self._username = username
        self._password = password
        self._force_close = force_close
        self._pool = pool
        self._loop = loop
        if not self._pool:
            force_release = False
        self._force_release = force_release

    def release(self):
        """Release connection to associated pool."""
        if self._pool:
            return self._pool.release(self)

    @property
    def conn(self):
        """Read only property for websocket connection.
        :returns: :py:class:`tornado.websocket.WebSocketClientConnection`
        """
        return self._conn

    @property
    def closed(self):
        """Readonly property. Return True if client has been closed
        or client connection has been closed
        :returns: bool
        """
        return self._closed or self._conn.closed

    def close(self):
        """Close the underlying websocket connection, detach from pool,
        and set to close.
        """
        self._closed = True
        self._pool = None
        return self._conn.close()

    def send(self, gremlin, bindings=None, lang="gremlin-groovy",
               aliases=None, op="eval", processor="", session=None,
               timeout=None, handler=None):
        """
        Send a script to the Gremlin Server.

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
        :param loop: If param is ``None``, `tornado.ioloop.IOLoop.current`
            is used for getting default event loop (optional)

        :returns: :py:class:`gremlinclient.connection.Stream` object
        """
        if session is None:
            session = self._session
        if timeout is None:
            timeout = self._timeout
        if aliases is None:
            aliases = {}
        message = self._prepare_message(
            gremlin, bindings, lang, aliases, op, processor, session)

        self.conn.send(message, binary=True)

        return Stream(self,
                      session,
                      processor,
                      handler,
                      self._loop,
                      self._username,
                      self._password,
                      self._force_close,
                      self._force_release,
                      self._future_class)

    def _prepare_message(self, gremlin, bindings, lang, aliases, op, processor,
                         session):
        message = {
            "requestId": str(uuid.uuid4()),
            "op": op,
            "processor": processor,
            "args": {
                "gremlin": gremlin,
                "bindings": bindings,
                "language":  lang,
                "aliases": aliases
            }
        }
        message = self._finalize_message(message, processor, session)
        return message

    def _authenticate(self, username, password, processor, session):
        auth = b"".join([b"\x00", username.encode("utf-8"),
                         b"\x00", password.encode("utf-8")])
        message = {
            "requestId": str(uuid.uuid4()),
            "op": "authentication",
            "processor": "",
            "args": {
                "sasl": base64.b64encode(auth).decode()
            }
        }
        message = self._finalize_message(message, processor, session)
        self.conn.send(message, binary=True)

    def _finalize_message(self, message, processor, session):
        if processor == "session":
            if session is None:
                raise RuntimeError("session processor requires a session id")
            else:
                message["args"].update({"session": session})
        message = json.dumps(message)
        return self._set_message_header(message, "application/json")

    @staticmethod
    def _set_message_header(message, mime_type):
        if mime_type == "application/json":
            mime_len = b"\x10"
            mime_type = b"application/json"
        else:
            raise ValueError("Unknown mime type.")
        return b"".join([mime_len, mime_type, message.encode("utf-8")])


class Session(Connection):
    """
    Child of :py:class:`gremlinclient.connection.Connection` object
    that is bound to a session that maintains state across messages with
    the server. Don't directly create Connection instances. Use
    :py:meth:`gremlinclient.graph.GraphDatabase.session` instead.

    :param tornado.websocket.WebSocketClientConnection conn: client
        websocket connection.
    :param float timeout: timeout for establishing connection (optional).
        Values ``0`` or ``None`` mean no timeout
    :param str username: Username for SASL auth
    :param str password: Password for SASL auth
    :param loop: If param is ``None``, `tornado.ioloop.IOLoop.current`
        is used for getting default event loop (optional)
    :param bool validate_cert: validate ssl certificate. False by default
    :param bool force_close: force connection to close after read.
    :param class future_class: type of Future -
        :py:class:`asyncio.Future`, :py:class:`trollius.Future`, or
        :py:class:`tornado.concurrent.Future`
    :param gremlinclient.pool.Pool pool: Connection pool. None by default
    :param bool force_release: If possible, force release to pool after read.
    :param str session: Session id (optional). Typically a uuid
    """
    def __init__(self, *args, **kwargs):
        super(Session, self).__init__(*args, **kwargs)
        if self._session is None:
            self._session = str(uuid.uuid4())

    def send(self, gremlin, bindings=None, lang="gremlin-groovy",
             aliases=None, op="eval", timeout=None, handler=None):
        """
        send a script to the Gremlin Server using sessions.

        :param str gremlin: Gremlin script to submit to server.
        :param dict bindings: A mapping of bindings for Gremlin script.
        :param str lang: Language of scripts submitted to the server.
            "gremlin-groovy" by default
        :param dict aliases: Rebind ``Graph`` and ``TraversalSource``
            objects to different variable names in the current request
        :param str op: Gremlin Server op argument. "eval" by default.
        :param float timeout: timeout for establishing connection (optional).
            Values ``0`` or ``None`` mean no timeout
        :param loop: If param is ``None``, `tornado.ioloop.IOLoop.current`
            is used for getting default event loop (optional)

        :returns: :py:class:`gremlinclient.connection.Stream` object
        """
        return super(Session, self).send(gremlin,
                                         bindings=bindings,
                                         lang=lang,
                                         aliases=aliases,
                                         op=op,
                                         timeout=timeout,
                                         processor="session",
                                         session=self._session,
                                         handler=handler)

    def _authenticate(self, username, password):
        super(Session, self)._authenticate(username,
                                           password,
                                           "session",
                                            self._session)


class Stream(object):
    """
    This object provides an interface for reading the response sent
    by the Gremlin Server over the websocket connection. Don't directly
    create stream instances, they should by returned by
    :py:meth:`gremlinclient.connection.Connection.send` or
    :py:meth:`gremlinclient.connection.Session.send`

    :param gremlinclient.connection.Connection conn: client
        websocket connection.
    :param str session: Session id. Typically a uuid
    :param str processor: Gremlin Server processor argument. "" by default.
    :param loop: If param is ``None``, `tornado.ioloop.IOLoop.current`
        is used for getting default event loop (optional)
    :param str username: Username for SASL auth
    :param str password: Password for SASL auth
    :param bool force_close: force connection to close after read.
    :param bool force_release: If possible, force release to pool after read.
    :param class future_class: type of Future -
        :py:class:`asyncio.Future`, :py:class:`trollius.Future`, or
        :py:class:`tornado.concurrent.Future`
    """

    def __init__(self, conn, session, processor, handler,
                 loop, username, password, force_close,
                 force_release, future_class):
        self._conn = conn
        self._session = session
        self._processor = processor
        self._closed = False
        self._username = username
        self._password = password
        self._force_close = force_close
        self._force_release = force_release
        self._loop = loop
        self._future_class = future_class or Future
        self._handlers = []
        if handler is not None:
            self._handlers.append(handler)

    def add_handler(self, handler):
        self._handlers.append(handler)

    def read(self):
        """
        Read a message from the response stream.

        :returns: Future -
            :py:class:`asyncio.Future`, :py:class:`trollius.Future`, or
            :py:class:`tornado.concurrent.Future`
        """
        future = self._future_class()
        if self._closed:
            future.set_result(None)
        elif self._conn.closed:
            future.set_exception(RuntimeError("Connection has been closed"))
        else:
            try:
                future = self._read(future)
            except Exception as e:
                future.set_exception(e)
        return future

    def _read(self, future):
        def parser(f):
            terminate = True
            try:
                result = f.result()
                # result can be none if conn is closed...test that
            except Exception as e:
                future.set_exception(e)
            else:
                message = json.loads(result.decode("utf-8"))
                message = Message(message["status"]["code"],
                                  message["result"]["data"],
                                  message["status"]["message"],
                                  message["result"]["meta"])
                status_code = message.status_code
                if status_code in [200, 206, 204]:
                    try:
                        message = self._process(message)
                    except Exception as e:
                        if self._force_close:
                            # This is a bit of a hack. What if close
                            # throws error asyncio.Cancelled ...
                            future_close = self._conn.close()
                            future_close.add_done_callback(
                                lambda f: future.set_exception(e))
                        elif self._force_release:
                            future_release = self._conn.release()
                            future_release.add_done_callback(
                                lambda f: future.set_exception(e))
                        else:
                            future.set_exception(e)
                    else:
                        if status_code == 206:
                            terminate = False
                            future.set_result(message)
                        elif self._force_close:
                            future_close = self._conn.close()
                            future_close.add_done_callback(
                                lambda f: future.set_result(message))
                        elif self._force_release:
                            future_release = self._conn.release()
                            future_release.add_done_callback(
                                lambda f: future.set_result(message))
                        else:
                            future.set_result(message)
                elif status_code == 407:
                    terminate = False
                    try:
                        self._conn._authenticate(
                            self._username, self._password, self._processor,
                            self._session)
                    except Exception as e:
                        future.set_exception(e)
                    else:
                        future_read = self.read()
                        def cb(f):
                            try:
                                result = f.result()
                            except Exception as e:
                                future.set_exception(e)
                            else:
                                future.set_result(result)
                        future_read.add_done_callback(cb)
                elif self._force_close:
                    future_close = self._conn.close()
                    future_close.add_done_callback(
                        lambda f: future.set_exception(
                            RuntimeError("{0} {1}".format(
                                message.status_code, message.message))))
                elif self._force_release:
                    future_release = self._conn.release()
                    future_release.add_done_callback(
                        lambda f: future.set_exception(
                            RuntimeError("{0} {1}".format(
                                message.status_code, message.message))))
                else:
                    future.set_exception(
                        RuntimeError("{0} {1}".format(
                            message.status_code, message.message)))
            finally:
                if terminate:
                    self._closed = True
                    self._conn = None

        future_resp = self._conn.conn.receive(callback=parser)
        return future

    def _process(self, message):
        if self._handlers:
            message = message.data
            for handler in self._handlers:
                message = handler(message)
        return message
