import socket
from tornado.concurrent import Future
from tornado.websocket import websocket_connect

from gremlinclient.base import AbstractBaseFactory
from gremlinclient.connection import GremlinConnection
from gremlinclient.manager import _FactoryConnectionContextManager


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

    def connect(self, force_close=False):

        future = Future()

        future_conn = websocket_connect(self._url)

        def get_conn(f):
            try:
                conn = f.result()
            except socket.error as e:
                future.set_exception(e)
            else:
                gc = GremlinConnection(conn, self._lang, self._processor,
                                       self._timeout, self._username,
                                       self._password, force_close=force_close)
                future.set_result(gc)

        future_conn.add_done_callback(get_conn)

        return future

    def connection(self):
        conn = self.connect()
        return _FactoryConnectionContextManager(conn)
