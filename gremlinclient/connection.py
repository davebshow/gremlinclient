import base64
import collections
import json
import uuid

from tornado import concurrent
from tornado.ioloop import IOLoop


Message = collections.namedtuple(
    "Message",
    ["status_code", "data", "message", "metadata"])


class Connection(object):
    """This class encapsulates a connection to the Gremlin Server.

    :param tornado.websocket.WebSocketClientConnection conn: client
        websocket connection.
    :param str lang: Language of scripts submitted to the server.
        "gremlin-groovy" by default
    :param str processor: Gremlin Server processor argument. "" by default.
    :param float timeout: timeout for establishing connection (optional).
        Values ``0`` or ``None`` mean no timeout
    :param str username: Username for SASL auth
    :param str password: Password for SASL auth
    :param loop: If param is ``None``, `tornado.ioloop.IOLoop.current`
        is used for getting default event loop (optional)
    :param bool validate_cert: validate ssl certificate. False by default
    :param bool force_close: force connection to close after read.
    :param class future_class: Type of Future - asyncio, trollius, or tornado.
        :py:class: tornado.concurrent.Future by default
    :param gremlinclient.pool.Pool pool: Connection pool. None by default
    :param bool force_release: If possible, force release to pool after read.
    :param str session: Session id (optional). Typically a uuid
    """
    def __init__(self, conn, timeout=None, username="", password="",
                 loop=None, validate_cert=False, force_close=False,
                 future_class=None, pool=None, force_release=False,
                 session=None):
        self._conn = conn
        self._closed = False
        self._session = session
        self._timeout = timeout
        self._username = username
        self._password = password
        self._force_close = force_close
        self._force_release = force_release
        self._loop = loop or IOLoop.current()
        self._pool = pool
        self._future_class = future_class or concurrent.Future

    def release(self):
        """Release connection to associated pool."""
        if self._pool:
            self._pool.release(self)

    @property
    def conn(self):
        """Read only property for websocket connection.
        :returns: :py:class:`tornado.websocket.WebSocketClientConnection`
        """
        return self._conn

    @property
    def closed(self):
        """Readonly property. Return True if client has been closed
        :returns: bool
        """
        return self._closed or self._conn.protocol is None

    def close(self):
        """Close the underlying websocket connection, detach from pool,
        and set to close.
        """
        self._conn.close()
        self._closed = True
        self._pool = None

    def submit(self, gremlin, bindings=None, lang="gremlin-groovy",
               aliases=None, op="eval", processor="", session=None,
               timeout=None):
        """
        Submit a script to the Gremlin Server.
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

        self.conn.write_message(message, binary=True)

        return Stream(self,
                      session,
                      processor,
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
        message = self._finalize_message(message, session, processor)
        return message

    def _authenticate(self, username, password, session, processor):
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
        message = self._finalize_message(message, session, processor)
        self.conn.write_message(message, binary=True)

    def _finalize_message(self, message, session, processor):
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


class Stream(object):
    """

    """

    def __init__(self, conn, session, processor, loop, username, password,
                 force_close, force_release, future_class):
        self._conn = conn
        self._session = session
        self._processor = processor
        self._closed = False
        self._username = username
        self._password = password
        self._force_close = force_close
        self._force_release = force_release
        self._loop = loop or IOLoop.current()
        self._future_class = future_class or concurrent.Future

    def read(self):
        future = self._future_class()
        if self._closed:
            future.set_result(None)
        elif self._conn.closed:
            future.set_exception(RuntimeError("Connection has been closed"))
        else:
            future = self._read(future)
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
                if message.status_code == 200:
                    future.set_result(message)
                elif message.status_code == 206:
                    terminate = False
                    future.set_result(message)
                elif message.status_code == 407:
                    terminate = False
                    try:
                        self._conn._authenticate(
                            self._username, self._password, self._session,
                            self._processor)
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
                elif message.status_code == 204:
                    future.set_result(message)
                else:
                    future.set_exception(
                        RuntimeError("{0} {1}".format(
                            message.status_code, message.message)))
            finally:
                if terminate:
                    if  self._force_close:
                        self._conn.close()
                    if self._force_release:
                        self._conn.release()
                    self._closed = True
                    self._conn = None


        future_resp = self._conn.conn.read_message(callback=parser)
        return future
