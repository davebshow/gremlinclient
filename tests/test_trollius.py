import unittest

import trollius
from trollius import From
from trollius import Future

import tornado
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.websocket import WebSocketClientConnection
from gremlinclient import (
    submit, GraphDatabase, Pool, Stream, create_connection)


AsyncIOMainLoop().install()


class TrolliusFactoryConnectTest(unittest.TestCase):

    def setUp(self):
        self.loop = trollius.get_event_loop()
        self.graph = GraphDatabase("ws://localhost:8182/",
                                   username="stephen",
                                   password="password",
                                   loop=self.loop,
                                   future_class=Future)


    def test_connect(self):

        @trollius.coroutine
        def go():
            connection = yield From(self.graph.connect())
            conn = connection.conn
            self.assertIsNotNone(conn.protocol)
            self.assertIsInstance(conn, WebSocketClientConnection)
            conn.close()

        self.loop.run_until_complete(go())


    def test_bad_port_exception(self):
        graph = GraphDatabase(url="ws://localhost:81/", loop=self.loop,
                              future_class=Future)

        @trollius.coroutine
        def go():
            with self.assertRaises(RuntimeError):
                connection = yield From(graph.connect())

        self.loop.run_until_complete(go())


    def test_wrong_protocol_exception(self):
        graph = GraphDatabase(url="wss://localhost:8182/", loop=self.loop,
                              future_class=Future)
        @trollius.coroutine
        def go():
            with self.assertRaises(RuntimeError):
                connection = yield From(graph.connect())

        self.loop.run_until_complete(go())


    def test_bad_host_exception(self):
        graph = GraphDatabase(url="ws://locaost:8182/", loop=self.loop,
                              future_class=Future)

        @trollius.coroutine
        def go():
            with self.assertRaises(RuntimeError):
                connection = yield From(graph.connect())

        self.loop.run_until_complete(go())

    def test_submit(self):

        @trollius.coroutine
        def go():
            connection = yield From(self.graph.connect())
            resp = connection.submit("1 + 1")
            while True:
                msg = yield From(resp.read())
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)
            connection.conn.close()

        self.loop.run_until_complete(go())

    def test_read_one_on_closed(self):

        @trollius.coroutine
        def go():
            connection = yield From(self.graph.connect())
            resp = connection.submit("1 + 1")
            connection.close()
            with self.assertRaises(RuntimeError):
                msg = yield From(resp.read())

        self.loop.run_until_complete(go())

    def test_null_read_on_closed(self):

        @trollius.coroutine
        def go():
            connection = yield From(self.graph.connect())
            # build connection
            connection.close()
            stream = Stream(connection, future_class=Future)
            with self.assertRaises(RuntimeError):
                msg = yield From(stream.read())

        self.loop.run_until_complete(go())

    # def test_creditials_error(self):
    #
    #     @trollius.coroutine
    #     def go():
    #         graph = GraphDatabase("ws://localhost:8182/",
    #                               username="stephen",
    #                               password="passwor",
    #                               loop=self.loop,
    #                               future_class=Future)
    #         connection = yield From(graph.connect())
    #         resp = connection.submit("1 + 1")
    #         with self.assertRaises(RuntimeError):
    #             msg = yield From(resp.read())
    #         connection.conn.close()
    #
    #     self.loop.run_until_complete(go())

    def test_force_close(self):

        @trollius.coroutine
        def go():
            connection = yield From(self.graph.connect(force_close=True))
            resp = connection.submit("1 + 1")
            while True:
                msg = yield From(resp.read())
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)
            self.assertIsNone(connection.conn.protocol)

        self.loop.run_until_complete(go())


class TrolliusPoolTest(unittest.TestCase):

    def setUp(self):
        self.loop = trollius.get_event_loop()

    def test_acquire(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop,
                    future_class=Future)

        @trollius.coroutine
        def go():
            connection = yield From(pool.acquire())
            conn = connection.conn
            self.assertIsNotNone(conn.protocol)
            self.assertIsInstance(conn, WebSocketClientConnection)
            self.assertEqual(pool.size, 1)
            self.assertTrue(connection in pool._acquired)
            connection2 = yield From(pool.acquire())
            conn2 = connection.conn
            self.assertIsNotNone(conn2.protocol)
            self.assertIsInstance(conn2, WebSocketClientConnection)
            self.assertEqual(pool.size, 2)
            self.assertTrue(connection2 in pool._acquired)
            conn.close()
            conn2.close()

        self.loop.run_until_complete(go())


    def test_acquire_submit(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop,
                    future_class=Future)

        @trollius.coroutine
        def go():
            connection = yield From(pool.acquire())
            resp = connection.submit("1 + 1")
            while True:
                msg = yield From(resp.read())
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)
            connection.conn.close()

        self.loop.run_until_complete(go())

    def test_maxsize(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop,
                    future_class=Future)

        @trollius.coroutine
        def go():
            c1 = yield From(pool.acquire())
            c2 = yield From(pool.acquire())
            c3 = pool.acquire()
            self.assertIsInstance(c3, Future)
            with self.assertRaises(trollius.TimeoutError):
                yield From(trollius.wait_for(c3, 0.1))
            c1.conn.close()
            c2.conn.close()

        self.loop.run_until_complete(go())

    def test_release(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop,
                    future_class=Future)

        @trollius.coroutine
        def go():
            self.assertEqual(len(pool.pool), 0)
            c1 = yield From(pool.acquire())
            self.assertEqual(len(pool._acquired), 1)
            pool.release(c1)
            self.assertEqual(len(pool.pool), 1)
            self.assertEqual(len(pool._acquired), 0)

        self.loop.run_until_complete(go())

    def test_release_closed(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    future_class=Future)
        self.assertEqual(len(pool.pool), 0)

        @trollius.coroutine
        def go():
            c1 = yield From(pool.acquire())
            self.assertEqual(len(pool._acquired), 1)
            c1.close()
            pool.release(c1)
            self.assertEqual(len(pool.pool), 0)
            self.assertEqual(len(pool._acquired), 0)
        self.loop.run_until_complete(go())

    def test_self_release(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    force_release=True,
                    future_class=Future,
                    loop=self.loop)

        @trollius.coroutine
        def go():
            self.assertEqual(len(pool.pool), 0)
            c1 = yield From(pool.acquire())
            self.assertEqual(len(pool._acquired), 1)
            stream = c1.submit("1 + 1")
            resp = yield From(stream.read())
            self.assertEqual(len(pool.pool), 1)
            self.assertEqual(len(pool._acquired), 0)

        self.loop.run_until_complete(go())

    def test_maxsize_release(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    future_class=Future)

        @trollius.coroutine
        def go():
            c1 = yield From(pool.acquire())
            c2 = yield From(pool.acquire())
            c3 = pool.acquire()
            self.assertIsInstance(c3, Future)
            with self.assertRaises(trollius.TimeoutError):
                shielded_fut = trollius.shield(c3)
                yield From(trollius.wait_for(shielded_fut, 0.1))
            pool.release(c2)
            c3 = yield From(c3)
            self.assertEqual(c2, c3)
            c1.conn.close()
            c2.conn.close()
            c3.conn.close()

        self.loop.run_until_complete(go())

    def test_close(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    future_class=Future)

        @trollius.coroutine
        def go():
            c1 = yield From(pool.acquire())
            c2 = yield From(pool.acquire())
            pool.release(c2)
            pool.close()
            self.assertIsNone(c2.conn.protocol)
            self.assertIsNotNone(c1.conn.protocol)
            c1.close()

        self.loop.run_until_complete(go())

    def test_cancelled(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    future_class=Future)

        @trollius.coroutine
        def go():
            c1 = yield From(pool.acquire())
            c2 = yield From(pool.acquire())
            c3 = pool.acquire()
            pool.close()
            self.assertTrue(c3.cancelled())
            c1.close()
            c2.close()

        self.loop.run_until_complete(go())

class TrolliusCtxtMngrTest(unittest.TestCase):

    def setUp(self):
        self.loop = trollius.get_event_loop()

    def test_pool_manager(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop,
                    future_class=Future)

        @trollius.coroutine
        def go():
            with (yield From(pool)) as conn:
                self.assertFalse(conn.closed)
            self.assertEqual(len(pool.pool), 1)
            self.assertEqual(len(pool._acquired), 0)
            pool.close()

    def test_graph_manager(self):
        graph = GraphDatabase(url="ws://localhost:8182/",
                              username="stephen",
                              password="password",
                              loop=self.loop,
                              future_class=Future)

        @trollius.coroutine
        def go():
            with (yield From(graph)) as conn:
                self.assertFalse(conn.closed)

class TrolliusCallbackStyleTest(unittest.TestCase):

    def setUp(self):
        self.loop = trollius.get_event_loop()

    def test_data_flow(self):

        def execute(script):
            future = Future()
            graph = GraphDatabase(url="ws://localhost:8182/",
                                  username="stephen",
                                  password="password",
                                  loop=self.loop,
                                  future_class=Future)
            future_conn = graph.connect()

            def cb(f):
                conn = f.result()
                stream = conn.submit(script)
                future.set_result(stream)

            future_conn.add_done_callback(cb)

            return future

        @trollius.coroutine
        def go():
            result = yield From(execute("1 + 1"))
            self.assertIsInstance(result, Stream)
            resp = yield From(result.read())
            self.assertEqual(resp.data[0], 2)

        self.loop.run_until_complete(go())


class TrolliusAPITests(unittest.TestCase):

    def setUp(self):
        self.loop = trollius.get_event_loop()

    def test_create_connection(self):

        @trollius.coroutine
        def go():
            conn = yield From(create_connection(
                url="ws://localhost:8182/", password="password",
                username="stephen", loop=self.loop, future_class=Future))
            self.assertIsNotNone(conn.conn.protocol)
            conn.close()

        self.loop.run_until_complete(go())


    def test_submit(self):

        @trollius.coroutine
        def go():
            stream = yield From(submit(
                "1 + 1", url="ws://localhost:8182/",
                password="password", username="stephen", loop=self.loop,
                future_class=Future))
            while True:
                msg = yield From(stream.read())
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)

        self.loop.run_until_complete(go())

    def test_script_exception(self):

        @trollius.coroutine
        def go():
            with self.assertRaises(RuntimeError):
                stream = yield From(submit("throw new Exception('error')",
                                      url="ws://localhost:8182/",
                                      password="password", username="stephen",
                                      loop=self.loop, future_class=Future))
                yield From(stream.read())

        self.loop.run_until_complete(go())



if __name__ == "__main__":
    unittest.main()
