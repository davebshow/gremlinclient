import collections
import json
import uuid
from tornado.websocket import websocket_connect
from tornado.concurrent import Future
# from tornado.platform.asyncio import to_asyncio_future
#
# try:
#     import asyncio
# except ImportError:
#     import trollius as asyncio

Message = collections.namedtuple(
    "Message",
    ["status_code", "data", "message", "metadata"])


class GremlinClient:
    """Main interface for interacting with the Gremlin Server.
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
    def __init__(self, url='ws://localhost:8182/', loop=None,
                 lang="gremlin-groovy", processor="", timeout=None,
                 username="", password="", save_errors=False):
        self._lang = lang
        self._processor = processor
        self._closed = False
        self._session = None
        self._url = url
        self._timeout = timeout
        self._username = username
        self._password = password
        self._save_errors = save_errors

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
               op="eval", processor=None, binary=True, session=None,
               timeout=None):
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
        :returns: :py:class:`gremlinclient.client.GremlinResponse` object
        """
        lang = lang or self.lang
        processor = processor or self.processor
        if session is None:
            session = self._session
        if timeout is None:
            timeout = self._timeout
        if rebindings is None:
            rebindings = {}

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
        future = Future()
        future_conn = websocket_connect(self.url)

        def send_message(f):
            conn = f.result()
            conn.write_message(message)
            future.set_result(GremlinResponse(conn, save_errors=self._save_errors))

        future_conn.add_done_callback(send_message)

        return future


class GremlinResponse:

    def __init__(self, conn, session=None, loop=None, username="",
                 password="", save_errors=False):
        self._conn = conn
        self._closed = False
        self._save_errors = save_errors

    def read(self):
        future = Future()
        if self._closed:
            future.set_result(None)
        else:
            future_resp = self._conn.read_message()

            def parser(f):
                message = json.loads(f.result())
                message = Message(message["status"]["code"],
                                  message["result"]["data"],
                                  message["status"]["message"],
                                  message["result"]["meta"])
                if message.status_code == 200:
                    future.set_result(message)
                    self._closed = True
                elif message.status_code == 206 or message.status_code == 407:
                    future.set_result(message)
                elif message.status_code == 204:
                    future.set_result(message)
                    self._closed = True
                elif self._save_errors:
                    future.set_result(message)
                    self._closed = True
                else:
                    future.cancel()
                    raise RuntimeError(
                        "{0} {1}".format(message.status_code, message.message))

            future_resp.add_done_callback(parser)
        return future


def submit(gremlin,
           url='ws://localhost:8182/',
           bindings=None,
           lang="gremlin-groovy",
           rebindings=None,
           op="eval",
           processor="",
           timeout=None,
           session=None,
           loop=None,
           username="",
           password="",
           save_errors=False):

    gc = GremlinClient(url=url, username=username, password=password, save_errors=save_errors)
    try:
        future_resp = gc.submit(gremlin, bindings=bindings, lang=lang,
                                rebindings=rebindings, op=op,
                                processor=processor, session=session,
                                timeout=timeout)
        return future_resp
    finally:
        gc.close()
