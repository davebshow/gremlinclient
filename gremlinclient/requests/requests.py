from concurrent import futures
from requests_futures.sessions import FuturesSession

from gremlinclient.connection import Connection, Session
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

    HEADERS = {'content-type': 'application/json'}

    def __init__(self, url, session, future_class):
        super().__init__(session, future_class)
        self._url = url
        self._closed = False
        self._future = None

    @property
    def conn(self):
        """
        :returns: Underlying connection.
        """
        return self._session

    @property
    def closed(self):
        """
        :returns: Connection protocol. None if conn is closed
        """
        return self._closed

    def close(self):
        self._closed = True

    def send(self, msg):
        """
        Send a message

        :param msg: The message to be sent.
        """
        self._future = self._session.post(self._url, data=msg, self.HEADERS)

    def receive(self, callback=None):
        """
        Read a message off the websocket.
        :param callback: To be called on message read.

        :returns: :py:class:`tornado.concurrent.Future`
        """
        self._closed = True
        return self._future


class Connection(Connection):

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
        message = json.dumps({
            "gremlin": gremlin,
            "bindings": bindings,
            "language": lang})

        self.conn.send(message)

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


class GraphDatabase(GraphDatabase):

    def __init__(self, url, timeout=None, username="", password="",
                 loop=None, verify_ssl=False, future_class=None):
        super().__init__(url, timeout=timeout, username=username,
                         password=password, loop=loop,
                         validate_cert=verify_ssl, future_class=futures.Future)
        self._session = FuturesSession()

    def session(self):
        raise NotImplementedError

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

    def _connect(self,
                 conn_type,
                 session,
                 force_close,
                 force_release,
                 pool):
        future = self._future_class()
        resp = Response(url, self._session, self._future_class,
                        loop=self._loop)
        gc = conn_type(resp, self._future_class, self._timeout,
                       self._username, self._password, self._loop,
                       self._validate_cert, False, pool, force_release,
                       session)
        future.set_result(gc)
        return future

    def close(self):
        self._session.close()


class Pool(Pool):
    def __init__(self, url, timeout=None, username="", password="",
                 maxsize=256, loop=None, force_release=False,
                 future_class=None):
        super().__init__(url, timeout=timeout, username=username,
                         password=password, graph_class=GraphDatabase,
                         maxsize=maxsize, loop=loop)

    def close(self):
        self._graph.close()
