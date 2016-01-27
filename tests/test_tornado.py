from datetime import timedelta
import unittest
import tornado
from tornado import gen
from tornado.concurrent import Future
from tornado.websocket import WebSocketClientConnection
from tornado.testing import gen_test, AsyncTestCase
from tornado.ioloop import IOLoop
from gremlinclient import GremlinFactory
from gremlinclient import GremlinPool
from gremlinclient import GremlinStream


class TornadoFactoryConnectTest(AsyncTestCase):

    def setUp(self):
        super(TornadoFactoryConnectTest, self).setUp()
        self.factory = GremlinFactory()

    @gen_test
    def test_connect(self):
        connection = yield self.factory.connect()
        conn = connection.conn
        self.assertIsNotNone(conn.protocol)
        self.assertIsInstance(conn, WebSocketClientConnection)
        conn.close()

    @gen_test
    def test_submit(self):
        connection = yield self.factory.connect()
        resp = connection.submit("1 + 1")
        while True:
            msg = yield resp.read()
            if msg is None:
                break
            self.assertEqual(msg.status_code, 200)
            self.assertEqual(msg.data[0], 2)
        connection.conn.close()

class TornadoPoolTest(AsyncTestCase):

    @gen_test
    def test_acquire(self):
        pool = GremlinPool(maxsize=2)
        connection = yield pool.acquire()
        conn = connection.conn
        self.assertIsNotNone(conn.protocol)
        self.assertIsInstance(conn, WebSocketClientConnection)
        self.assertEqual(pool.size, 1)
        self.assertTrue(connection in pool._acquired)
        connection2 = yield pool.acquire()
        conn2 = connection.conn
        self.assertIsNotNone(conn2.protocol)
        self.assertIsInstance(conn2, WebSocketClientConnection)
        self.assertEqual(pool.size, 2)
        self.assertTrue(connection2 in pool._acquired)
        conn.close()
        conn2.close()

    @gen_test
    def test_acquire_submit(self):
        pool = GremlinPool(maxsize=2)
        connection = yield pool.acquire()
        resp = connection.submit("1 + 1")
        while True:
            msg = yield resp.read()
            if msg is None:
                break
            self.assertEqual(msg.status_code, 200)
            self.assertEqual(msg.data[0], 2)
        connection.conn.close()

    @gen_test
    def test_maxsize(self):
        pool = GremlinPool(maxsize=2)
        c1 = yield pool.acquire()
        c2 = yield pool.acquire()
        c3 = pool.acquire()
        self.assertIsInstance(c3, Future)
        try:
            yield gen.with_timeout(timedelta(seconds=0.1), c3)
            error = False
        except tornado.gen.TimeoutError:
            error = True
        self.assertTrue(error)
        c1.conn.close()
        c2.conn.close()

    @gen_test
    def test_release(self):
        pool = GremlinPool(maxsize=2)
        self.assertEqual(len(pool.pool), 0)
        c1 = yield pool.acquire()
        self.assertEqual(len(pool._acquired), 1)
        pool.release(c1)
        self.assertEqual(len(pool.pool), 1)
        self.assertEqual(len(pool._acquired), 0)

    @gen_test
    def test_maxsize_release(self):
        pool = GremlinPool(maxsize=2)
        c1 = yield pool.acquire()
        c2 = yield pool.acquire()
        c3 = pool.acquire()
        self.assertIsInstance(c3, Future)
        try:
            yield gen.with_timeout(timedelta(seconds=0.1), c3)
            error = False
        except tornado.gen.TimeoutError:
            error = True
        self.assertTrue(error)
        pool.release(c2)
        c3 = yield c3
        self.assertEqual(c2, c3)
        c1.conn.close()
        c2.conn.close()
        c3.conn.close()

    @gen_test
    def test_close(self):
        pool = GremlinPool(maxsize=2)
        c1 = yield pool.acquire()
        c2 = yield pool.acquire()
        pool.release(c2)
        pool.close()
        self.assertIsNone(c2.conn.protocol)
        self.assertIsNotNone(c1.conn.protocol)
        c1.close()

    @gen_test
    def test_cancelled(self):
        pool = GremlinPool(maxsize=2)
        c1 = yield pool.acquire()
        c2 = yield pool.acquire()
        c3 = pool.acquire()
        pool.close()
        # Tornado futures do not support cancellation!
        # self.assertTrue(c3.cancelled())
        c1.close()
        c2.close()


class TornadoCallbackStyleTest(AsyncTestCase):

    def setUp(self):
        super(TornadoCallbackStyleTest, self).setUp()
        self.pool = GremlinPool()

    @gen_test
    def test_data_flow(self):

        def execute(script):
            future = Future()
            factory = GremlinFactory()
            future_conn = factory.connect()

            def cb(f):
                conn = f.result()
                stream = conn.submit(script)
                future.set_result(stream)

            future_conn.add_done_callback(cb)

            return future

        result = yield execute("1 + 1")
        self.assertIsInstance(result, GremlinStream)
        resp = yield result.read()
        self.assertEqual(resp.data[0], 2)

    # def setUp(self):
    #     super(Py27SyntaxTest, self).setUp()
    #     self.loop = IOLoop.current()
    #
    # @gen_test
    # def test_submit(self):
    #
    #     fut = submit("1 + 1")
    #     res = yield fut
    #     while True:
    #         msg = yield res.read()
    #         if msg is None:
    #             break
    #         self.assertEqual(msg.status_code, 200)
    #         self.assertEqual(msg.data[0], 2)
    #
    # @gen_test(timeout=1)
    # def test_exception(self):
    #
    #     with self.assertRaises(RuntimeError):
    #         fut = submit("throw new Exception('error')")
    #         res = yield fut
    #         while True:
    #             msg = yield res.read()
    #             if msg is None:
    #                 break
    #
    # # These should be gen_test
    # def test_add_handler(self):
    #
    #     class Dummy(object):
    #         def __init__(self):
    #             self.results = None
    #
    #         def req(self):
    #             future = Future()
    #             future_results = submit("1 + 1")
    #
    #             def process_results(results):
    #                 self.results = results.data
    #                 return results
    #
    #             def set_processor(f):
    #                 result = f.result()
    #                 result.add_handler(process_results)
    #                 future.set_result(result)
    #
    #             future_results.add_done_callback(set_processor)
    #
    #             return future
    #
    #     @gen.coroutine
    #     def go():
    #         dummy = Dummy()
    #         resp = yield dummy.req()
    #         while True:
    #             msg = yield resp.read()
    #             if msg is None:
    #                 break
    #             self.assertEqual(dummy.results, msg.data)
    #
    #     self.loop.run_sync(go)
    #
    #
    # def test_pass_handler(self):
    #
    #     class Dummy(object):
    #         def __init__(self):
    #             self.results = None
    #
    #         def req(self, cond):
    #
    #             def process_results(results):
    #                 if not cond:
    #                     self.results = results.data
    #                 return results
    #
    #             future_results = submit("1 + 1", handler=process_results)
    #
    #             return future_results
    #
    #     @gen.coroutine
    #     def go():
    #         dummy = Dummy()
    #         resp = yield dummy.req(False)
    #         while True:
    #             msg = yield resp.read()
    #             if msg is None:
    #                 break
    #             self.assertEqual(dummy.results, msg.data)
    #
    #     self.loop.run_sync(go)


if __name__ == "__main__":
    unittest.main()
