from datetime import timedelta
import unittest

from tornado import gen
from tornado.concurrent import Future
from tornado.process import Subprocess
from tornado.websocket import WebSocketClientConnection
from tornado.ioloop import IOLoop

from gremlinclient import (
    submit, GraphDatabase, Pool, Stream, create_connection)


# setUp/tearDown/get_new_ioloop based on:
# http://www.tornadoweb.org/en/stable/_modules/tornado/testing.html#AsyncTestCase


class TornadoFactoryConnectTest(unittest.TestCase):

    def setUp(self):
        super(TornadoFactoryConnectTest, self).setUp()
        self.loop = self.get_new_ioloop()
        self.loop.make_current()
        self.graph = GraphDatabase("ws://localhost:8182/",
                                   username="stephen",
                                   password="password",
                                   loop=self.loop,
                                   future_class=Future)

    def tearDown(self):
        # Clean up Subprocess, so it can be used again with a new ioloop.
        Subprocess.uninitialize()
        self.loop.clear_current()
        if (not IOLoop.initialized() or
                self.loop is not IOLoop.instance()):
            # Try to clean up any file descriptors left open in the ioloop.
            # This avoids leaks, especially when tests are run repeatedly
            # in the same process with autoreload (because curl does not
            # set FD_CLOEXEC on its file descriptors)
            self.loop.close(all_fds=True)
        super(TornadoFactoryConnectTest, self).tearDown()


    def get_new_ioloop(self):
        """Creates a new `.IOLoop` for this test.  May be overridden in
        subclasses for tests that require a specific `.IOLoop` (usually
        the singleton `.IOLoop.instance()`).
        """
        return IOLoop()

    def test_connect(self):

        async def go():
            connection = await self.graph.connect()
            conn = connection.conn
            self.assertIsNotNone(conn.protocol)
            self.assertIsInstance(conn, WebSocketClientConnection)
            conn.close()

        self.loop.run_sync(go)


    def test_bad_port_exception(self):
        graph = GraphDatabase(url="ws://localhost:81/", loop=self.loop,
                              future_class=Future)

        async def go():
            with self.assertRaises(RuntimeError):
                connection = await graph.connect()

        self.loop.run_sync(go)


    def test_wrong_protocol_exception(self):
        graph = GraphDatabase(url="wss://localhost:8182/", loop=self.loop,
                              future_class=Future)

        async def go():
            with self.assertRaises(RuntimeError):
                connection = await graph.connect()

        self.loop.run_sync(go)


    def test_bad_host_exception(self):
        graph = GraphDatabase(url="ws://locaost:8182/", loop=self.loop,
                              future_class=Future)

        async def go():
            with self.assertRaises(RuntimeError):
                connection = await graph.connect()

        self.loop.run_sync(go)

    def test_submit(self):

        async def go():
            connection = await self.graph.connect()
            resp = connection.submit("1 + 1")
            while True:
                msg = await resp.read()
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)
            connection.conn.close()

        self.loop.run_sync(go)

    def test_read_one_on_closed(self):

        async def go():
            connection = await self.graph.connect()
            resp = connection.submit("1 + 1")
            connection.close()
            with self.assertRaises(RuntimeError):
                msg = await resp.read()

        self.loop.run_sync(go)

    def test_null_read_on_closed(self):

        async def go():
            connection = await self.graph.connect()
            # build connection
            connection.close()
            stream = Stream(connection, future_class=Future)
            with self.assertRaises(RuntimeError):
                msg = await stream.read()

        self.loop.run_sync(go)

    # def test_creditials_error(self):
    #
    #
    #     async def go():
    #         graph = GraphDatabase("ws://localhost:8182/",
    #                               username="stephen",
    #                               password="passwor",
    #                               loop=self.loop,
    #                               future_class=Future)
    #         connection = await graph.connect()
    #         resp = connection.submit("1 + 1")
    #         with self.assertRaises(RuntimeError):
    #             msg = await resp.read()
    #         connection.conn.close()
    #
    #     self.loop.run_sync(go)

    def test_force_close(self):

        async def go():
            connection = await self.graph.connect(force_close=True)
            resp = connection.submit("1 + 1")
            while True:
                msg = await resp.read()
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)
            self.assertIsNone(connection.conn.protocol)

        self.loop.run_sync(go)


class TornadoPoolTest(unittest.TestCase):

    def setUp(self):
        super(TornadoPoolTest, self).setUp()
        self.loop = self.get_new_ioloop()
        self.loop.make_current()

    def tearDown(self):
        # Clean up Subprocess, so it can be used again with a new ioloop.
        Subprocess.uninitialize()
        self.loop.clear_current()
        if (not IOLoop.initialized() or
                self.loop is not IOLoop.instance()):
            # Try to clean up any file descriptors left open in the ioloop.
            # This avoids leaks, especially when tests are run repeatedly
            # in the same process with autoreload (because curl does not
            # set FD_CLOEXEC on its file descriptors)
            self.loop.close(all_fds=True)
        super(TornadoPoolTest, self).tearDown()


    def get_new_ioloop(self):
        """Creates a new `.IOLoop` for this test.  May be overridden in
        subclasses for tests that require a specific `.IOLoop` (usually
        the singleton `.IOLoop.instance()`).
        """
        return IOLoop()

    def test_acquire(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop,
                    future_class=Future)

        async def go():
            connection = await pool.acquire()
            conn = connection.conn
            self.assertIsNotNone(conn.protocol)
            self.assertIsInstance(conn, WebSocketClientConnection)
            self.assertEqual(pool.size, 1)
            self.assertTrue(connection in pool._acquired)
            connection2 = await pool.acquire()
            conn2 = connection.conn
            self.assertIsNotNone(conn2.protocol)
            self.assertIsInstance(conn2, WebSocketClientConnection)
            self.assertEqual(pool.size, 2)
            self.assertTrue(connection2 in pool._acquired)
            conn.close()
            conn2.close()

        self.loop.run_sync(go)


    def test_acquire_submit(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop,
                    future_class=Future)

        async def go():
            connection = await pool.acquire()
            resp = connection.submit("1 + 1")
            while True:
                msg = await resp.read()
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)
            connection.conn.close()

        self.loop.run_sync(go)

    def test_maxsize(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop,
                    future_class=Future)

        async def go():
            c1 = await pool.acquire()
            c2 = await pool.acquire()
            c3 = pool.acquire()
            self.assertIsInstance(c3, Future)
            with self.assertRaises(gen.TimeoutError):
                await gen.with_timeout(timedelta(seconds=0.1), c3)
            c1.conn.close()
            c2.conn.close()

        self.loop.run_sync(go)

    def test_release(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop,
                    future_class=Future)

        async def go():
            self.assertEqual(len(pool.pool), 0)
            c1 = await pool.acquire()
            self.assertEqual(len(pool._acquired), 1)
            pool.release(c1)
            self.assertEqual(len(pool.pool), 1)
            self.assertEqual(len(pool._acquired), 0)

        self.loop.run_sync(go)

    def test_release_closed(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    future_class=Future)
        self.assertEqual(len(pool.pool), 0)

        async def go():
            c1 = await pool.acquire()
            self.assertEqual(len(pool._acquired), 1)
            c1.close()
            pool.release(c1)
            self.assertEqual(len(pool.pool), 0)
            self.assertEqual(len(pool._acquired), 0)
        self.loop.run_sync(go)

    def test_self_release(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    force_release=True,
                    future_class=Future,
                    loop=self.loop)

        async def go():
            self.assertEqual(len(pool.pool), 0)
            c1 = await pool.acquire()
            self.assertEqual(len(pool._acquired), 1)
            stream = c1.submit("1 + 1")
            resp = await stream.read()
            self.assertEqual(len(pool.pool), 1)
            self.assertEqual(len(pool._acquired), 0)

        self.loop.run_sync(go)

    def test_maxsize_release(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    future_class=Future)

        async def go():
            c1 = await pool.acquire()
            c2 = await pool.acquire()
            c3 = pool.acquire()
            self.assertIsInstance(c3, Future)
            with self.assertRaises(gen.TimeoutError):
                await gen.with_timeout(timedelta(seconds=0.1), c3)
            pool.release(c2)
            c3 = await c3
            self.assertEqual(c2, c3)
            c1.conn.close()
            c2.conn.close()
            c3.conn.close()

        self.loop.run_sync(go)

    def test_close(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    future_class=Future)

        async def go():
            c1 = await pool.acquire()
            c2 = await pool.acquire()
            pool.release(c2)
            pool.close()
            self.assertIsNone(c2.conn.protocol)
            self.assertIsNotNone(c1.conn.protocol)
            c1.close()

        self.loop.run_sync(go)

    def test_cancelled(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    future_class=Future)

        async def go():
            c1 = await pool.acquire()
            c2 = await pool.acquire()
            c3 = pool.acquire()
            pool.close()
            # Tornado futures don't support cancellation
            # self.assertTrue(c3.cancelled())
            c1.close()
            c2.close()

        self.loop.run_sync(go)

class TornadoCnxtMngrTest(unittest.TestCase):

    def setUp(self):
        super(TornadoCnxtMngrTest, self).setUp()
        self.loop = self.get_new_ioloop()
        self.loop.make_current()

    def tearDown(self):
        # Clean up Subprocess, so it can be used again with a new ioloop.
        Subprocess.uninitialize()
        self.loop.clear_current()
        if (not IOLoop.initialized() or
                self.loop is not IOLoop.instance()):
            # Try to clean up any file descriptors left open in the ioloop.
            # This avoids leaks, especially when tests are run repeatedly
            # in the same process with autoreload (because curl does not
            # set FD_CLOEXEC on its file descriptors)
            self.loop.close(all_fds=True)
        super(TornadoCnxtMngrTest, self).tearDown()


    def get_new_ioloop(self):
        """Creates a new `.IOLoop` for this test.  May be overridden in
        subclasses for tests that require a specific `.IOLoop` (usually
        the singleton `.IOLoop.instance()`).
        """
        return IOLoop()

    def test_pool_manager(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop,
                    future_class=Future)

        async def go():
            with await pool as conn:
                self.assertFalse(conn.closed)
            self.assertEqual(len(pool.pool), 1)
            self.assertEqual(len(pool._acquired), 0)
            pool.close()

    # def test_pool_manager_async_with(self):
    #     pool = Pool(url="ws://localhost:8182/",
    #                 maxsize=2,
    #                 username="stephen",
    #                 password="password",
    #                 loop=self.loop,
    #                 future_class=Future)
    #
    #     async def go():
    #         async with pool.connection() as conn:
    #             self.assertFalse(conn.closed)
    #         self.assertEqual(len(pool.pool), 1)
    #         self.assertEqual(len(pool._acquired), 0)
    #         pool.close()
    #     self.loop.run_sync(go)

    def test_graph_manager(self):
        graph = GraphDatabase(url="ws://localhost:8182/",
                              username="stephen",
                              password="password",
                              loop=self.loop,
                              future_class=Future)

        async def go():
            with await graph as conn:
                self.assertFalse(conn.closed)

        self.loop.run_sync(go)

class TornadoCallbackStyleTest(unittest.TestCase):

    def setUp(self):
        super(TornadoCallbackStyleTest, self).setUp()
        self.loop = self.get_new_ioloop()
        self.loop.make_current()

    def tearDown(self):
        # Clean up Subprocess, so it can be used again with a new ioloop.
        Subprocess.uninitialize()
        self.loop.clear_current()
        if (not IOLoop.initialized() or
                self.loop is not IOLoop.instance()):
            # Try to clean up any file descriptors left open in the ioloop.
            # This avoids leaks, especially when tests are run repeatedly
            # in the same process with autoreload (because curl does not
            # set FD_CLOEXEC on its file descriptors)
            self.loop.close(all_fds=True)
        super(TornadoCallbackStyleTest, self).tearDown()


    def get_new_ioloop(self):
        """Creates a new `.IOLoop` for this test.  May be overridden in
        subclasses for tests that require a specific `.IOLoop` (usually
        the singleton `.IOLoop.instance()`).
        """
        return IOLoop()

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

        async def go():
            result = await execute("1 + 1")
            self.assertIsInstance(result, Stream)
            resp = await result.read()
            self.assertEqual(resp.data[0], 2)

        self.loop.run_sync(go)


class TornadoAPITest(unittest.TestCase):

    def setUp(self):
        super(TornadoAPITest, self).setUp()
        self.loop = self.get_new_ioloop()
        self.loop.make_current()

    def tearDown(self):
        # Clean up Subprocess, so it can be used again with a new ioloop.
        Subprocess.uninitialize()
        self.loop.clear_current()
        if (not IOLoop.initialized() or
                self.loop is not IOLoop.instance()):
            # Try to clean up any file descriptors left open in the ioloop.
            # This avoids leaks, especially when tests are run repeatedly
            # in the same process with autoreload (because curl does not
            # set FD_CLOEXEC on its file descriptors)
            self.loop.close(all_fds=True)
        super(TornadoAPITest, self).tearDown()


    def get_new_ioloop(self):
        """Creates a new `.IOLoop` for this test.  May be overridden in
        subclasses for tests that require a specific `.IOLoop` (usually
        the singleton `.IOLoop.instance()`).
        """
        return IOLoop()

    def test_create_connection(self):

        async def go():
            conn = await create_connection(
                url="ws://localhost:8182/", password="password",
                username="stephen", loop=self.loop, future_class=Future)
            self.assertIsNotNone(conn.conn.protocol)
            conn.close()

        self.loop.run_sync(go)


    def test_submit(self):

        async def go():
            stream = await submit(
                "1 + 1", url="ws://localhost:8182/",
                password="password", username="stephen", loop=self.loop,
                future_class=Future)
            while True:
                msg = await stream.read()
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)

        self.loop.run_sync(go)

    def test_script_exception(self):

        async def go():
            with self.assertRaises(RuntimeError):
                stream = await submit("throw new Exception('error')",
                                      url="ws://localhost:8182/",
                                      password="password", username="stephen",
                                      loop=self.loop, future_class=Future)
                await stream.read()

        self.loop.run_sync(go)



if __name__ == "__main__":
    unittest.main()
