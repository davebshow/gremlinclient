import unittest
import trollius
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.platform.asyncio import to_asyncio_future
from gremlinclient import submit


class TrolliusSyntaxTest(unittest.TestCase):

    def setUp(self):
        AsyncIOMainLoop().install()
        self.loop = trollius.get_event_loop()

    def test_submit(self):

        @trollius.coroutine
        def go():
            f = submit("1 + 1")
            f = to_asyncio_future(f)
            resp = yield trollius.From(f)
            while True:
                msg = to_asyncio_future(resp.read())
                msg = yield trollius.From(msg)
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)

        self.loop.run_until_complete(go())


if __name__ == "__main__":
    unittest.main()
