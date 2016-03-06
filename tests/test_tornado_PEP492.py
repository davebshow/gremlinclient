import uuid
import unittest
from datetime import timedelta

from tornado import gen
from tornado.concurrent import Future
from tornado.process import Subprocess
from tornado.websocket import WebSocketClientConnection
from tornado.ioloop import IOLoop

from gremlinclient.connection import Stream
from gremlinclient.tornado import (
    submit, GraphDatabase, Pool, create_connection, Response)



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
            conn = connection.conn._conn
            self.assertIsNotNone(conn.protocol)
            self.assertIsInstance(conn, WebSocketClientConnection)
            conn.close()

        self.loop.run_sync(go)


    def test_bad_port_exception(self):
        graph = GraphDatabase("ws://localhost:81/", loop=self.loop,
                              future_class=Future)

        async def go():
            with self.assertRaises(RuntimeError):
                connection = await graph.connect()

        self.loop.run_sync(go)


    def test_wrong_protocol_exception(self):
        graph = GraphDatabase("wss://localhost:8182/", loop=self.loop,
                              future_class=Future)

        async def go():
            with self.assertRaises(RuntimeError):
                connection = await graph.connect()

        self.loop.run_sync(go)


    # def test_bad_host_exception(self):
    #     graph = GraphDatabase("ws://locaost:8182/", loop=self.loop,
    #                           future_class=Future)
    #
    #     async def go():
    #         with self.assertRaises(RuntimeError):
    #             connection = await graph.connect()
    #
    #     self.loop.run_sync(go)

    def test_send(self):

        async def go():
            connection = await self.graph.connect()
            resp = connection.send("1 + 1")
            while True:
                msg = await resp.read()
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)
            connection.conn.close()

        self.loop.run_sync(go)

    def test_handler(self):

        async def go():
            connection = await self.graph.connect()
            resp = connection.send("1 + 1", handler=lambda x: x[0] * 2)
            while True:
                msg = await resp.read()
                if msg is None:
                    break
                self.assertEqual(msg, 4)
            connection.conn.close()

        self.loop.run_sync(go)

    def test_add_handler(self):

        async def go():
            connection = await self.graph.connect()
            resp = connection.send("1 + 1", handler=lambda x: x[0] * 2)
            resp.add_handler(lambda x: x ** 2)
            while True:
                msg = await resp.read()
                if msg is None:
                    break
                self.assertEqual(msg, 16)
            connection.conn.close()

        self.loop.run_sync(go)

    def test_read_one_on_closed(self):

        async def go():
            connection = await self.graph.connect()
            resp = connection.send("1 + 1")
            connection.close()
            with self.assertRaises(RuntimeError):
                msg = await resp.read()

        self.loop.run_sync(go)

    def test_null_read_on_closed(self):

        async def go():
            connection = await self.graph.connect()
            # build connection
            connection.close()
            stream = Stream(connection, None, "processor", None, None, "stephen",
                            "password", False, False, Future)
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
    #         resp = connection.send("1 + 1")
    #         with self.assertRaises(RuntimeError):
    #             msg = await resp.read()
    #         connection.conn.close()
    #
    #     self.loop.run_sync(go)

    def test_force_close(self):

        async def go():
            connection = await self.graph.connect(force_close=True)
            resp = connection.send("1 + 1")
            while True:
                msg = await resp.read()
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)
            self.assertTrue(connection.conn.closed)

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
        pool = Pool("ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop,
                    future_class=Future)

        async def go():
            connection = await pool.acquire()
            conn = connection.conn
            self.assertFalse(conn.closed)
            self.assertIsInstance(conn, Response)
            self.assertEqual(pool.size, 1)
            self.assertTrue(connection in pool._acquired)
            connection2 = await pool.acquire()
            conn2 = connection.conn
            self.assertFalse(conn2.closed)
            self.assertIsInstance(conn2, Response)
            self.assertEqual(pool.size, 2)
            self.assertTrue(connection2 in pool._acquired)
            conn.close()
            conn2.close()

        self.loop.run_sync(go)


    def test_acquire_send(self):
        pool = Pool("ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop,
                    future_class=Future)

        async def go():
            connection = await pool.acquire()
            resp = connection.send("1 + 1")
            while True:
                msg = await resp.read()
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)
            connection.conn.close()

        self.loop.run_sync(go)

    def test_maxsize(self):
        pool = Pool("ws://localhost:8182/",
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
        pool = Pool("ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop,
                    future_class=Future)

        async def go():
            self.assertEqual(len(pool.pool), 0)
            c1 = await pool.acquire()
            self.assertEqual(len(pool._acquired), 1)
            await pool.release(c1)
            self.assertEqual(len(pool.pool), 1)
            self.assertEqual(len(pool._acquired), 0)

        self.loop.run_sync(go)

    def test_release_acquire(self):
        pool = Pool("ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    future_class=Future)

        async def go():
            c1 = await pool.acquire()
            await pool.release(c1)
            c2 = await pool.acquire()
            self.assertEqual(c1, c2)

        self.loop.run_sync(go)

    def test_release_closed(self):
        pool = Pool("ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    future_class=Future)
        self.assertEqual(len(pool.pool), 0)

        async def go():
            c1 = await pool.acquire()
            self.assertEqual(len(pool._acquired), 1)
            c1.close()
            await pool.release(c1)
            self.assertEqual(len(pool.pool), 0)
            self.assertEqual(len(pool._acquired), 0)
        self.loop.run_sync(go)

    def test_self_release(self):
        pool = Pool("ws://localhost:8182/",
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
            stream = c1.send("1 + 1")
            resp = await stream.read()
            self.assertEqual(len(pool.pool), 1)
            self.assertEqual(len(pool._acquired), 0)

        self.loop.run_sync(go)

    def test_maxsize_release(self):
        pool = Pool("ws://localhost:8182/",
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
            await pool.release(c2)
            c3 = await c3
            self.assertEqual(c2, c3)
            c1.conn.close()
            c2.conn.close()
            c3.conn.close()

        self.loop.run_sync(go)

    def test_pool_too_big(self):

        async def go():
            pool1 = Pool("ws://localhost:8182/",
                         maxsize=2,
                         username="stephen",
                         password="password",
                         future_class=Future)
            pool2 = Pool("ws://localhost:8182/",
                         username="stephen",
                         password="password",
                         future_class=Future)
            conn1 = await pool1.acquire()
            conn2 = await pool2.acquire()
            conn3 = await pool2.acquire()
            conn4 = await pool2.acquire()
            pool1.pool.append(conn2)
            pool1.pool.append(conn3)
            pool1.pool.append(conn4)
            await pool1.release(conn1)
            self.assertTrue(conn1.closed)

        self.loop.run_sync(go)

    def test_close(self):
        pool = Pool("ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    future_class=Future)

        async def go():
            c1 = await pool.acquire()
            c2 = await pool.acquire()
            await pool.release(c2)
            pool.close()
            self.assertTrue(c2.conn.closed)
            self.assertFalse(c1.conn.closed)
            c1.close()

        self.loop.run_sync(go)

    def test_cancelled(self):
        pool = Pool("ws://localhost:8182/",
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

# class TornadoCnxtMngrTest(unittest.TestCase):
#
#     def setUp(self):
#         super(TornadoCnxtMngrTest, self).setUp()
#         self.loop = self.get_new_ioloop()
#         self.loop.make_current()
#
#     def tearDown(self):
#         # Clean up Subprocess, so it can be used again with a new ioloop.
#         Subprocess.uninitialize()
#         self.loop.clear_current()
#         if (not IOLoop.initialized() or
#                 self.loop is not IOLoop.instance()):
#             # Try to clean up any file descriptors left open in the ioloop.
#             # This avoids leaks, especially when tests are run repeatedly
#             # in the same process with autoreload (because curl does not
#             # set FD_CLOEXEC on its file descriptors)
#             self.loop.close(all_fds=True)
#         super(TornadoCnxtMngrTest, self).tearDown()
#
#
#     def get_new_ioloop(self):
#         """Creates a new `.IOLoop` for this test.  May be overridden in
#         subclasses for tests that require a specific `.IOLoop` (usually
#         the singleton `.IOLoop.instance()`).
#         """
#         return IOLoop()
#
#     def test_pool_manager(self):
#         pool = Pool("ws://localhost:8182/",
#                     maxsize=2,
#                     username="stephen",
#                     password="password",
#                     loop=self.loop,
#                     future_class=Future)
#
#         async def go():
#             with await pool as conn:
#                 self.assertFalse(conn.closed)
#             self.assertEqual(len(pool.pool), 1)
#             self.assertEqual(len(pool._acquired), 0)
#             pool.close()
#
#     # def test_pool_manager_async_with(self):
    #     pool = Pool("ws://localhost:8182/",
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

    # def test_graph_manager(self):
    #     graph = GraphDatabase("ws://localhost:8182/",
    #                           username="stephen",
    #                           password="password",
    #                           loop=self.loop,
    #                           future_class=Future)
    #
    #     async def go():
    #         with await graph as conn:
    #             self.assertFalse(conn.closed)
    #
    #     self.loop.run_sync(go)
    #
    # def test_pool_enter_runtime_error(self):
    #     pool = Pool("ws://localhost:8182/",
    #                 maxsize=2,
    #                 username="stephen",
    #                 password="password",
    #                 future_class=Future)
    #     with self.assertRaises(RuntimeError):
    #         with pool as conn:
    #             self.assertFalse(conn.closed)
    #
    # def test_conn_enter_runtime_error(self):
    #     graph = GraphDatabase("ws://localhost:8182/",
    #                           username="stephen",
    #                           password="password",
    #                           future_class=Future)
    #     with self.assertRaises(RuntimeError):
    #         with graph as conn:
    #             self.assertFalse(conn.closed)


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
            graph = GraphDatabase("ws://localhost:8182/",
                                  username="stephen",
                                  password="password",
                                  loop=self.loop,
                                  future_class=Future)
            future_conn = graph.connect()

            def cb(f):
                conn = f.result()
                stream = conn.send(script)
                future.set_result(stream)

            future_conn.add_done_callback(cb)

            return future

        async def go():
            result = await execute("1 + 1")
            self.assertIsInstance(result, Stream)
            resp = await result.read()
            self.assertEqual(resp.data[0], 2)

        self.loop.run_sync(go)


class TornadoSessionTest(unittest.TestCase):

    def setUp(self):
        super(TornadoSessionTest, self).setUp()
        self.loop = self.get_new_ioloop()
        self.loop.make_current()
        self.graph = GraphDatabase("ws://localhost:8182/",
                                   username="stephen",
                                   password="password",
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
        super(TornadoSessionTest, self).tearDown()

    def get_new_ioloop(self):
        """Creates a new `.IOLoop` for this test.  May be overridden in
        subclasses for tests that require a specific `.IOLoop` (usually
        the singleton `.IOLoop.instance()`).
        """
        return IOLoop()

    def test_manual_session(self):

        async def go():
            session = await self.graph.connect(session=str(uuid.uuid4()))
            stream = session.send("v = 1+1", processor="session")
            resp = await stream.read()
            stream = session.send("v", processor="session")
            resp2 = await stream.read()
            self.assertEqual(resp.data[0], resp2.data[0])
            session.close()

        self.loop.run_sync(go)

    def test_no_session(self):

        async def go():
            session = await self.graph.connect()
            with self.assertRaises(RuntimeError):
                stream = session.send("v = 1+1", processor="session")

        self.loop.run_sync(go)

    def test_session_obj_session(self):

        async def go():
            session = await self.graph.session()
            stream = session.send("v = 1+1")
            resp = await stream.read()
            stream = session.send("v")
            resp2 = await stream.read()
            self.assertEqual(resp.data[0], resp2.data[0])

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
                "ws://localhost:8182/", password="password",
                username="stephen", loop=self.loop, future_class=Future)
            self.assertFalse(conn.conn.closed)
            conn.close()

        self.loop.run_sync(go)


    def test_submit(self):

        async def go():
            stream = await submit(
                "ws://localhost:8182/", "1 + 1",
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
                stream = await submit("ws://localhost:8182/",
                                      "throw new Exception('error')",
                                      password="password", username="stephen",
                                      loop=self.loop, future_class=Future)
                await stream.read()

        self.loop.run_sync(go)



if __name__ == "__main__":
    unittest.main()
