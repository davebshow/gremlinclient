import base64
import collections
import json
import uuid

from tornado import concurrent
from tornado.ioloop import IOLoop

from gremlinclient.base import AbstractBaseConnection


Message = collections.namedtuple(
    "Message",
    ["status_code", "data", "message", "metadata"])


class Connection(AbstractBaseConnection):
    """This class encapsulates a connection to the Gremlin Server using the
    Tornado websocket client implementation.
    :param str url: url for Gremlin Server (optional). 'http://localhost:8182/'
        by default
    :param loop:
    :param str lang: Language of scripts submitted to the server.
        "gremlin-groovy" by default
    :param str op: Gremlin Server op argument. "eval" by default.
    :param str processor: Gremlin Server processor argument. "" by default.
    :param float timeout: timeout for establishing connection (optional).
        Values ``0`` or ``None`` mean no timeout
    :param connector: A class that implements the method ``ws_connect``.
        Usually an instance of ``aiogremlin.connector.GremlinConnector``
    """
    def __init__(self, conn, lang="gremlin-groovy", processor="",
                 timeout=None, username="", password="", loop=None,
                 validate_cert=False, future_class=None, pool=None,
                 force_close=False, force_release=False):
        self._conn = conn
        self._lang = lang
        self._processor = processor
        self._closed = False
        self._session = None
        self._timeout = timeout
        self._username = username
        self._password = password
        self._force_close = force_close
        self._force_release = force_release
        self._loop = loop or IOLoop.current()
        self._pool = pool
        self._future_class = future_class or concurrent.Future

    def release(self):
        if self._pool:
            self._pool.release(self)

    @property
    def conn(self):
        return self._conn

    @property
    def processor(self):
        """Readonly property. The processor argument for Gremlin
        Server"""
        return self._processor

    @property
    def lang(self):
        """Readonly property. The language used for Gremlin scripts"""
        return self._lang

    @property
    def url(self):
        """Getter for database url used by the client"""
        return self._url

    @property
    def closed(self):
        """Readonly property. Return True if client has been closed"""
        return self._closed or self._conn.protocol is None

    def close(self):
        self._conn.close()
        self._closed = True
        self._pool = None

    def submit(self, gremlin, bindings=None, lang=None, rebindings=None,
               op="eval", processor=None, session=None,
               timeout=None, mime_type="application/json"):
        """
        Submit a script to the Gremlin Server.
        :param str gremlin: Gremlin script to submit to server.
        :param dict bindings: A mapping of bindings for Gremlin script.
        :param str lang: Language of scripts submitted to the server.
            "gremlin-groovy" by default
        :param dict rebindings: Rebind ``Graph`` and ``TraversalSource``
            objects to different variable names in the current request
        :param str op: Gremlin Server op argument. "eval" by default.
        :param str processor: Gremlin Server processor argument. "" by default.
        :param float timeout: timeout for establishing connection (optional).
            Values ``0`` or ``None`` mean no timeout
        :param str session: Session id (optional). Typically a uuid
        :param loop: :ref:`event loop<asyncio-event-loop>` If param is ``None``
            `asyncio.get_event_loop` is used for getting default event loop
            (optional)
        :returns: :py:class:`gremlinclient.client.Stream` object
        """
        lang = lang or self.lang
        processor = processor or self.processor
        if session is None:
            session = self._session
        if timeout is None:
            timeout = self._timeout
        if rebindings is None:
            rebindings = {}

        message = self._prepare_message(
            gremlin, bindings=bindings, lang=lang, rebindings=rebindings,
            op=op, processor=processor, session=session)

        message = json.dumps(message)
        message = self._set_message_header(message, mime_type)
        self.conn.write_message(message, binary=True)

        return Stream(self,
                             force_close=self._force_close,
                             force_release=self._force_release,
                             username=self._username,
                             password=self._password,
                             future_class=self._future_class)

    @staticmethod
    def _prepare_message(gremlin, bindings, lang, rebindings, op, processor,
                         session):
        message = {
            "requestId": str(uuid.uuid4()),
            "op": op,
            "processor": processor,
            "args": {
                "gremlin": gremlin,
                "bindings": bindings,
                "language":  lang,
                "rebindings": rebindings
            }
        }
        if session is None:
            if processor == "session":
                raise RuntimeError("session processor requires a session id")
        else:
            message["args"].update({"session": session})
        return message

    @staticmethod
    def _set_message_header(message, mime_type):
        if mime_type == "application/json":
            mime_len = b"\x10"
            mime_type = b"application/json"
        else:
            raise ValueError("Unknown mime type.")
        return b"".join([mime_len, mime_type, message.encode("utf-8")])

    def _authenticate(self, username, password, session=None, processor=""):
        # Maybe join with submit to avoid repeating code.
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
        if session is None:
            if processor == "session":
                raise RuntimeError("session processor requires a session id")
        else:
            message["args"].update({"session": session})
        message = json.dumps(message)
        message = self._set_message_header(message, "application/json")
        return self.conn.write_message(message, binary=True)


class Stream(object):

    def __init__(self, conn, session=None, loop=None, username="",
                 password="", force_close=False,
                 force_release=False, future_class=None):
        self._conn = conn
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
                                self._username, self._password)
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
