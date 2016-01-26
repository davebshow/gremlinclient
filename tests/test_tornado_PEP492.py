import unittest
from tornado import gen
from tornado.websocket import WebSocketClientConnection
from tornado.ioloop import IOLoop
from gremlinclient import GremlinFactory


class TornadoPEP492SyntaxFactoryTest(unittest.TestCase):

    def setUp(self):
        self.loop = IOLoop.current()

    def test_connect(self):

        async def go():
            connection = GremlinFactory.connect()
            conn = await connection.conn
            self.assertIsNotNone(conn.protocol)
            self.assertIsInstance(conn, WebSocketClientConnection)
            conn.close()

        self.loop.run_sync(go)

    def test_submit(self):

        async def go():
            connection = GremlinFactory.connect()
            resp = await connection.submit("1 + 1")
            while True:
                msg = await resp.read()
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)

        self.loop.run_sync(go)

if __name__ == "__main__":
    unittest.main()
