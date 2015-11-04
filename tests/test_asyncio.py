import unittest
import asyncio
from tornado.websocket import WebSocketClientConnection
from tornado.platform.asyncio import AsyncIOMainLoop
from gremlinclient import aiosubmit


class AsyncioSyntaxTest(unittest.TestCase):

    def setUp(self):
        AsyncIOMainLoop().install()
        self.loop = asyncio.get_event_loop()

    def test_submit(self):

        @asyncio.coroutine
        def go():
            f = aiosubmit("1 + 1")
            resp = yield from f
            while True:
                msg = resp.read()
                msg = yield from msg
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)

        result = self.loop.run_until_complete(go())


if __name__ == "__main__":
    unittest.main()
