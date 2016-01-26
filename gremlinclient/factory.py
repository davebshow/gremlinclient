from tornado.concurrent import Future
from tornado.websocket import websocket_connect

from gremlinclient.base import AbstractBaseFactory
from gremlinclient.connection import GremlinConnection


class GremlinFactory(AbstractBaseFactory):
    """This class generates connections to the Gremlin Server"""

    def __init__(self, url='ws://localhost:8182/', lang="gremlin-groovy",
                 processor="", timeout=None, username="", password=""):
        self._url = url
        self._lang = lang
        self._processor = processor
        self._timeout = timeout
        self._username = username
        self._password = password

    def connect(self):

        future = Future()

        future_conn = websocket_connect(self._url)

        def get_conn(f):
            conn = f.result()
            gc = GremlinConnection(conn,
                                   self._lang,
                                   self._processor,
                                   self._timeout,
                                   self._username,
                                   self._password)
            future.set_result(gc)

        future_conn.add_done_callback(get_conn)

        return future
