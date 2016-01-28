import socket
from tornado.concurrent import Future
from tornado.httpclient import HTTPRequest, HTTPError
from tornado.ioloop import IOLoop
from tornado.websocket import websocket_connect

from gremlinclient.base import AbstractBaseFactory
from gremlinclient.connection import GremlinConnection
from gremlinclient.manager import _FactoryConnectionContextManager


class GremlinFactory(AbstractBaseFactory):
    """This class generates connections to the Gremlin Server"""

    def __init__(self, url='ws://localhost:8182/', lang="gremlin-groovy",
                 processor="", timeout=None, username="", password="",
                 loop=None, validate_cert=False):
        self._url = url
        self._lang = lang
        self._processor = processor
        self._timeout = timeout
        self._username = username
        self._password = password
        self._loop = loop or IOLoop.current()
        self._validate_cert = validate_cert

    def connect(self, force_close=False):
        request = HTTPRequest(self._url, validate_cert=self._validate_cert)
        future = Future()
        future_conn = websocket_connect(request)

        def get_conn(f):
            try:
                conn = f.result()
            except socket.error as e:
                future.set_exception(e)
            except socket.gaierror as e:
                future.set_exception(e)
            except HTTPError as e:
                future.set_exception(e)
            else:
                gc = GremlinConnection(conn, self._lang, self._processor,
                                       self._timeout, self._username,
                                       self._password, force_close=force_close)
                future.set_result(gc)

        self._loop.add_future(future_conn, get_conn)
        return future

    def connection(self):
        conn = self.connect()
        return _FactoryConnectionContextManager(conn)
