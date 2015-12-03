import unittest
import tornado
from tornado import gen
from tornado.concurrent import Future
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

    # These should be gen_test
    def test_add_handler(self):

        class Dummy(object):
            def __init__(self):
                self.results = None

            def req(self):
                future = Future()
                future_results = submit("1 + 1")

                def process_results(results):
                    self.results = results.data
                    return results

                def set_processor(f):
                    result = f.result()
                    result.add_handler(process_results)
                    future.set_result(result)

                future_results.add_done_callback(set_processor)

                return future

        @gen.coroutine
        def go():
            dummy = Dummy()
            resp = yield dummy.req()
            while True:
                msg = yield resp.read()
                if msg is None:
                    break
                self.assertEqual(dummy.results, msg.data)

        self.loop.run_sync(go)


    def test_pass_handler(self):

        class Dummy(object):
            def __init__(self):
                self.results = None

            def req(self, cond):

                def process_results(results):
                    if not cond:
                        self.results = results.data
                    return results

                future_results = submit("1 + 1", handler=process_results)

                return future_results

        @gen.coroutine
        def go():
            dummy = Dummy()
            resp = yield dummy.req(False)
            while True:
                msg = yield resp.read()
                if msg is None:
                    break
                self.assertEqual(dummy.results, msg.data)

        self.loop.run_sync(go)


if __name__ == "__main__":
    unittest.main()
