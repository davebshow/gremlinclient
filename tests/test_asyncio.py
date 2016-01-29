import asyncio
import socket
import unittest
from datetime import timedelta
import tornado
from tornado import gen
from tornado.concurrent import Future
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.websocket import WebSocketClientConnection
from tornado.testing import gen_test, AsyncTestCase
from tornado.ioloop import IOLoop
from gremlinclient import (
    submit, GremlinFactory, GremlinPool, GremlinStream, create_connection)



class AsyncioSyntaxTest(unittest.TestCase):

    def setUp(self):
        AsyncIOMainLoop().install()
        self.loop = asyncio.get_event_loop()
        self.factory = GremlinFactory("wss://localhost:8182/",
                                      username="stephen",
                                      password="password",
                                      future_class=asyncio.Future)


    def test_connect(self):

        @asyncio.coroutine
        def go():
            connection = yield from self.factory.connect()
            conn = connection.conn
            self.assertIsNotNone(conn.protocol)
            self.assertIsInstance(conn, WebSocketClientConnection)
            conn.close()


if __name__ == "__main__":
    unittest.main()
