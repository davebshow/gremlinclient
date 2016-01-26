from gremlinclient.base import AbstractBaseFactory
from gremlinclient.connection import GremlinConnection

from tornado.websocket import websocket_connect


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

        future_conn = websocket_connect(self._url)

        return GremlinConnection(
            future_conn, self._lang, self._processor, self._timeout,
            self._username, self._password)
