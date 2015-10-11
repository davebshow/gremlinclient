import unittest
from tornado import gen
from tornado.ioloop import IOLoop
from gremlinclient import submit


class Py27SyntaxTest(unittest.TestCase):

    def setUp(self):
        self.loop = IOLoop.current()

    def test_submit(self):

        @gen.coroutine
        def go():
            f = submit("1 + 1")
            res = yield f
            while True:
                msg = yield res.read()
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)

        self.loop.run_sync(go)

if __name__ == "__main__":
    unittest.main()
