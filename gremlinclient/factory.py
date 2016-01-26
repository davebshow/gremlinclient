from gremlinclient.base import AbstractBaseFactory
from gremlinclient.connection import GremlinConnection

from tornado.websocket import websocket_connect


class GremlinFactory(AbstractBaseFactory):
    """This class generates connections to the Gremlin Server"""

    @classmethod
    def connect(cls, url='ws://localhost:8182/',
                lang="gremlin-groovy",
                processor="",
                timeout=None,
                username="",
                password=""):

        future_conn = websocket_connect(url)

        return GremlinConnection(
            future_conn, lang, processor, timeout, username, password)
