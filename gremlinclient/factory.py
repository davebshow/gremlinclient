import socket
import sys

from tornado import concurrent
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
                 loop=None, validate_cert=False, future_type=None):
        self._url = url
        self._lang = lang
        self._processor = processor
        self._timeout = timeout
        self._username = username
        self._password = password
        self._loop = loop or IOLoop.current()
        self._validate_cert = validate_cert
        self._future = future_type or concurrent.Future

    def connect(self, force_close=False, force_release=False, pool=None):
        request = HTTPRequest(self._url, validate_cert=self._validate_cert)
        future = self._future()
        future_conn = websocket_connect(request)

        def get_conn(f):
            try:
                conn = f.result()
            except socket.error:
                future.set_exc_info(sys.exc_info())
            except socket.gaierror:
                future.set_exc_info(sys.exc_info())
            except HTTPError:
                future.set_exc_info(sys.exc_info())
            else:
                gc = GremlinConnection(conn, self._lang, self._processor,
                                       self._timeout, self._username,
                                       self._password, force_close=force_close,
                                       force_release=force_release, pool=pool,
                                       future_type=self._future)
                future.set_result(gc)
        future_conn.add_done_callback(get_conn)
        return future

    def connection(self):
        conn = self.connect()
        return _FactoryConnectionContextManager(conn)
