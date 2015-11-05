import unittest
from tornado import gen
from tornado.ioloop import IOLoop
from gremlinclient import submit


class TornadoPEP492SyntaxTest(unittest.TestCase):

    def setUp(self):
        self.loop = IOLoop.current()

    def test_submit(self):

        async def go():
            res = await submit("1 + 1")
            while True:
                msg = await res.read()
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)

        self.loop.run_sync(go)

if __name__ == "__main__":
    unittest.main()
