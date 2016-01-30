import unittest
from datetime import timedelta
import tornado
from tornado import gen
from tornado.concurrent import Future
from tornado.websocket import WebSocketClientConnection
from tornado.testing import gen_test, AsyncTestCase
from tornado.ioloop import IOLoop
from gremlinclient import (
    submit, GraphDatabase, Pool, Stream, create_connection)


class TornadoFactoryConnectTest(AsyncTestCase):

    def setUp(self):
        super(TornadoFactoryConnectTest, self).setUp()
        self.graph = GraphDatabase("ws://localhost:8182/",
                                      username="stephen",
                                      password="password")

    @gen_test
    def test_connect(self):
        connection = yield self.graph.connect()
        conn = connection.conn
        self.assertIsNotNone(conn.protocol)
        self.assertIsInstance(conn, WebSocketClientConnection)
        conn.close()

    @gen_test
    def test_bad_port_exception(self):
        graph = GraphDatabase(url="ws://localhost:81/")
        with self.assertRaises(RuntimeError):
            connection = yield graph.connect()

    @gen_test
    def test_wrong_protocol_exception(self):
        graph = GraphDatabase(url="wss://localhost:8182/")
        # with self.assertRaises(tornado.httpclient.HTTPError)
        with self.assertRaises(RuntimeError):
            connection = yield graph.connect()

    @gen_test
    def test_bad_host_exception(self):
        graph = GraphDatabase(url="ws://locaost:8182/")
        with self.assertRaises(RuntimeError):
            connection = yield graph.connect()

    @gen_test
    def test_submit(self):
        connection = yield self.graph.connect()
        resp = connection.submit("1 + 1")
        while True:
            msg = yield resp.read()
            if msg is None:
                break
            self.assertEqual(msg.status_code, 200)
            self.assertEqual(msg.data[0], 2)
        connection.conn.close()

    @gen_test
    def test_read_one_on_closed(self):
        connection = yield self.graph.connect()
        resp = connection.submit("1 + 1")
        connection.close()
        with self.assertRaises(RuntimeError):
            msg = yield resp.read()

    @gen_test
    def test_null_read_on_closed(self):
        connection = yield self.graph.connect()
        # build connection
        connection.close()
        stream = Stream(connection)
        with self.assertRaises(RuntimeError):
            msg = yield stream.read()

    # @gen_test
    # def test_creditials_error(self):
    #     graph = GraphDatabase("ws://localhost:8182/",
    #                             username="stephen",
    #                             password="passwor")
    #     connection = yield graph.connect()
    #     resp = connection.submit("1 + 1")
    #     with self.assertRaises(RuntimeError):
    #         msg = yield resp.read()
    #     connection.conn.close()

    @gen_test
    def test_force_close(self):
        connection = yield self.graph.connect(force_close=True)
        resp = connection.submit("1 + 1")
        while True:
            msg = yield resp.read()
            if msg is None:
                break
            self.assertEqual(msg.status_code, 200)
            self.assertEqual(msg.data[0], 2)
        self.assertIsNone(connection.conn.protocol)

class TornadoPoolTest(AsyncTestCase):

    @gen_test
    def test_acquire(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password")
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
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password")
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
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password")
        c1 = yield pool.acquire()
        c2 = yield pool.acquire()
        c3 = pool.acquire()
        self.assertIsInstance(c3, Future)
        with self.assertRaises(tornado.gen.TimeoutError):
            yield gen.with_timeout(timedelta(seconds=0.1), c3)
        c1.conn.close()
        c2.conn.close()

    @gen_test
    def test_release(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password")
        self.assertEqual(len(pool.pool), 0)
        c1 = yield pool.acquire()
        self.assertEqual(len(pool._acquired), 1)
        pool.release(c1)
        self.assertEqual(len(pool.pool), 1)
        self.assertEqual(len(pool._acquired), 0)

    @gen_test
    def test_self_release(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    force_release=True)
        self.assertEqual(len(pool.pool), 0)
        c1 = yield pool.acquire()
        self.assertEqual(len(pool._acquired), 1)
        stream = c1.submit("1 + 1")
        resp = yield stream.read()
        self.assertEqual(len(pool.pool), 1)
        self.assertEqual(len(pool._acquired), 0)

    @gen_test
    def test_maxsize_release(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password")
        c1 = yield pool.acquire()
        c2 = yield pool.acquire()
        c3 = pool.acquire()
        self.assertIsInstance(c3, Future)
        with self.assertRaises(tornado.gen.TimeoutError):
            yield gen.with_timeout(timedelta(seconds=0.1), c3)
        pool.release(c2)
        c3 = yield c3
        self.assertEqual(c2, c3)
        c1.conn.close()
        c2.conn.close()
        c3.conn.close()

    @gen_test
    def test_close(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password")
        c1 = yield pool.acquire()
        c2 = yield pool.acquire()
        pool.release(c2)
        pool.close()
        self.assertIsNone(c2.conn.protocol)
        self.assertIsNotNone(c1.conn.protocol)
        c1.close()

    @gen_test
    def test_cancelled(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password")
        c1 = yield pool.acquire()
        c2 = yield pool.acquire()
        c3 = pool.acquire()
        pool.close()
        # Tornado futures do not support cancellation!
        # self.assertTrue(c3.cancelled())
        c1.close()
        c2.close()


class TornadoCtxtMngrTest(AsyncTestCase):

    @gen_test
    def test_pool_manager(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password")
        with (yield pool) as conn:
            self.assertFalse(conn.closed)
        self.assertEqual(len(pool.pool), 1)
        self.assertEqual(len(pool._acquired), 0)
        pool.close()

    @gen_test
    def test_graph_manager(self):
        graph = GraphDatabase(url="ws://localhost:8182/",
                                username="stephen",
                                password="password")
        with (yield graph) as conn:
            self.assertFalse(conn.closed)

class TornadoCallbackStyleTest(AsyncTestCase):

    def setUp(self):
        super(TornadoCallbackStyleTest, self).setUp()
        self.pool = Pool()

    @gen_test
    def test_data_flow(self):

        def execute(script):
            future = Future()
            graph = GraphDatabase(url="ws://localhost:8182/",
                                    username="stephen",
                                    password="password")
            future_conn = graph.connect()

            def cb(f):
                conn = f.result()
                stream = conn.submit(script)
                future.set_result(stream)

            future_conn.add_done_callback(cb)

            return future

        result = yield execute("1 + 1")
        self.assertIsInstance(result, Stream)
        resp = yield result.read()
        self.assertEqual(resp.data[0], 2)


class TornadoAPITests(AsyncTestCase):

    @gen_test
    def test_create_connection(self):
        conn = yield create_connection(
            url="ws://localhost:8182/", password="password",
            username="stephen")
        self.assertIsNotNone(conn.conn.protocol)
        conn.close()

    @gen_test
    def test_submit(self):
        stream = yield submit(
            "1 + 1", url="ws://localhost:8182/",
            password="password", username="stephen")
        while True:
            msg = yield stream.read()
            if msg is None:
                break
            self.assertEqual(msg.status_code, 200)
            self.assertEqual(msg.data[0], 2)

    @gen_test(timeout=1)
    def test_script_exception(self):
        with self.assertRaises(RuntimeError):
            stream = yield submit("throw new Exception('error')",
                                  url="ws://localhost:8182/",
                                  password="password", username="stephen")
            yield stream.read()


if __name__ == "__main__":
    unittest.main()
