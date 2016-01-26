import collections
import json
import uuid

from tornado.concurrent import Future

from gremlinclient.base import AbstractBaseConnection


Message = collections.namedtuple(
    "Message",
    ["status_code", "data", "message", "metadata"])


class GremlinConnection(AbstractBaseConnection):
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
    def __init__(self, conn, lang, processor, timeout, username,
                 password):
        self._conn = conn
        self._lang = lang
        self._processor = processor
        self._closed = False
        self._session = None
        self._timeout = timeout
        self._username = username
        self._password = password
        self._open = bool(conn.protocol)

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
        """Getter/setter for database url used by the client"""
        return self._url

    @url.setter
    def url(self, value):
        self._url = value

    @property
    def closed(self):
        """Readonly property. Return True if client has been closed"""
        pass

    def close(self):
        pass

    def submit(self, gremlin, bindings=None, lang=None, rebindings=None,
               op="eval", processor=None, session=None,
               timeout=None, mime_type="application/json", handler=None):
        """
        :ref:`coroutine<coroutine>` method.
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
        :returns: :py:class:`gremlinclient.client.GremlinStream` object
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
        message = self._set_message_header(message, mime_type)

        future = Future()

        self.conn.write_message(message, binary=True)
        
        future.set_result(GremlinStream(self.conn, handler=handler))


        return future

    @staticmethod
    def _prepare_message(gremlin, bindings, lang, rebindings, op, processor,
                         session):
        message = json.dumps({
            "requestId": str(uuid.uuid4()),
            "op": op,
            "processor": processor,
            "args": {
                "gremlin": gremlin,
                "bindings": bindings,
                "language":  lang,
                "rebindings": rebindings
            }
        })
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


class GremlinStream(object):

    def __init__(self, conn, session=None, loop=None, username="",
                 password="", handler=None):
        self._conn = conn
        self._closed = False
        self._username = username
        self._password = password
        self._handler = handler

    def add_handler(self, func):
        self._handler = func

    def read(self):
        future = Future()
        if self._closed:
            future.set_result(None)
        else:

            future_resp = self._conn.read_message()

            def parser(f):
                message = json.loads(f.result().decode("utf-8"))
                message = Message(message["status"]["code"],
                                  message["result"]["data"],
                                  message["status"]["message"],
                                  message["result"]["meta"])
                if self._handler is None:
                    self._handler = lambda x: x
                if message.status_code == 200:
                    future.set_result(self._handler(message))
                    # self._conn.close(code=1000)
                    self._closed = True
                    self._conn = None
                elif message.status_code == 206:
                    future.set_result(self._handler(message))
                elif message.status_code == 407:
                    # Set up auth/ssl here
                    pass
                elif message.status_code == 204:
                    future.set_result(self._handler(message))
                    # self._conn.close(code=1000)
                    self._closed = True
                    self._conn = None
                else:
                    future.set_exception(RuntimeError(
                        "{0} {1}".format(message.status_code, message.message)))
                    # self._conn.close(code=1006)
                    self._closed = True
                    self._conn = None

            future_resp.add_done_callback(parser)
        return future

    # @staticmethod
    # def _authenticate(username, password, session, processor):
    #     auth = b"".join([b"\x00", bytes(username, "utf-8"), b"\x00", bytes(password, "utf-8")])
    #     message = {
    #         "requestId": str(uuid.uuid4()),
    #         "op": "authentication",
    #         "processor": processor,
    #         "args": {
    #             "sasl": base64.b64encode(auth).decode()
    #         }
    #     }
    #     if session is None:
    #         if processor == "session":
    #             raise RuntimeError("session processor requires a session id")
    #     else:
    #         message["args"].update({"session": session})
    #     return message


# def submit(gremlin,
#            url='ws://localhost:8182/',
#            bindings=None,
#            lang="gremlin-groovy",
#            rebindings=None,
#            op="eval",
#            processor="",
#            timeout=None,
#            session=None,
#            loop=None,
#            username="",
#            password="",
#            handler=None):
#
#     gc = GremlinConnection(url=url, username=username, password=password)
#     try:
#         future_resp = gc.submit(gremlin, bindings=bindings, lang=lang,
#                                 rebindings=rebindings, op=op,
#                                 processor=processor, session=session,
#                                 timeout=timeout, handler=handler)
#         return future_resp
#     finally:
#         gc.close()
