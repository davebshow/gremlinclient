import unittest
import tornado
from tornado.testing import gen_test
from tornado.ioloop import IOLoop
from gremlinclient import submit


class Py27SyntaxTest(tornado.testing.AsyncTestCase):

    def setUp(self):
        super(Py27SyntaxTest, self).setUp()
        self.loop = IOLoop.current()

    @gen_test
    def test_submit(self):

        fut = submit("1 + 1")
        res = yield fut
        while True:
            msg = yield res.read()
            if msg is None:
                break
            self.assertEqual(msg.status_code, 200)
            self.assertEqual(msg.data[0], 2)

    @gen_test(timeout=1)
    def test_exception(self):

        with self.assertRaises(RuntimeError):
            fut = submit("throw new Exception('error')")
            res = yield fut
            while True:
                msg = yield res.read()
                if msg is None:
                    break



if __name__ == "__main__":
    unittest.main()
