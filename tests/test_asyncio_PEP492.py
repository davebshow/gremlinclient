import asyncio
from asyncio import Future
import uuid
import unittest

import tornado
from tornado.websocket import WebSocketClientConnection
from tornado.platform.asyncio import AsyncIOMainLoop

from gremlinclient import (
    submit, GraphDatabase, Pool, Stream, create_connection, Response)


AsyncIOMainLoop().install()


class AsyncioFactoryConnectTest(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.graph = GraphDatabase("ws://localhost:8182/",
                                   username="stephen",
                                   password="password",
                                   loop=self.loop,
                                   future_class=Future)


    def test_connect(self):

        async def go():
            connection = await self.graph.connect()
            conn = connection.conn._conn
            self.assertIsNotNone(conn.protocol)
            self.assertIsInstance(conn, WebSocketClientConnection)
            conn.close()

        self.loop.run_until_complete(go())


    def test_bad_port_exception(self):
        graph = GraphDatabase(url="ws://localhost:81/", loop=self.loop,
                              future_class=Future)

        async def go():
            with self.assertRaises(RuntimeError):
                connection = await graph.connect()

        self.loop.run_until_complete(go())


    def test_wrong_protocol_exception(self):
        graph = GraphDatabase(url="wss://localhost:8182/", loop=self.loop,
                              future_class=Future)

        async def go():
            with self.assertRaises(RuntimeError):
                connection = await graph.connect()

        self.loop.run_until_complete(go())


    # def test_bad_host_exception(self):
    #     graph = GraphDatabase(url="ws://locaost:8182/", loop=self.loop,
    #                           future_class=Future)
    #
    #     async def go():
    #         with self.assertRaises(RuntimeError):
    #             connection = await graph.connect()
    #
    #     self.loop.run_until_complete(go())

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

        self.loop.run_until_complete(go())

    def test_handler(self):

        async def go():
            connection = await self.graph.connect()
            resp = connection.send("1 + 1", handler=lambda x: x.data[0] * 2)
            while True:
                msg = await resp.read()
                if msg is None:
                    break
                self.assertEqual(msg, 4)
            connection.conn.close()

        self.loop.run_until_complete(go())

    def test_read_one_on_closed(self):

        async def go():
            connection = await self.graph.connect()
            resp = connection.send("1 + 1")
            connection.close()
            with self.assertRaises(RuntimeError):
                msg = await resp.read()

        self.loop.run_until_complete(go())

    def test_null_read_on_closed(self):

        async def go():
            connection = await self.graph.connect()
            # build connection
            connection.close()
            stream = Stream(connection, None, "processor", None, None, "stephen",
                            "password", False, False, Future)
            with self.assertRaises(RuntimeError):
                msg = await stream.read()

        self.loop.run_until_complete(go())

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
    #     self.loop.run_until_complete(go())

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

        self.loop.run_until_complete(go())


class AsyncioPoolTest(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.get_event_loop()

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

        self.loop.run_until_complete(go())


    def test_acquire_send(self):
        pool = Pool(url="ws://localhost:8182/",
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

        self.loop.run_until_complete(go())

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
            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(c3, 0.1)
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

        async def go():
            self.assertEqual(len(pool.pool), 0)
            c1 = await pool.acquire()
            self.assertEqual(len(pool._acquired), 1)
            pool.release(c1)
            self.assertEqual(len(pool.pool), 1)
            self.assertEqual(len(pool._acquired), 0)

        self.loop.run_until_complete(go())

    def test_release_acquire(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    future_class=Future)

        async def go():
            c1 = await pool.acquire()
            pool.release(c1)
            c2 = await pool.acquire()
            self.assertEqual(c1, c2)

        self.loop.run_until_complete(go())

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
        self.loop.run_until_complete(go())

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
            stream = c1.send("1 + 1")
            resp = await stream.read()
            self.assertEqual(len(pool.pool), 1)
            self.assertEqual(len(pool._acquired), 0)

        self.loop.run_until_complete(go())

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
            with self.assertRaises(asyncio.TimeoutError):
                shielded_fut = asyncio.shield(c3)
                await asyncio.wait_for(shielded_fut, 0.1)
            pool.release(c2)
            c3 = await c3
            self.assertEqual(c2, c3)
            c1.conn.close()
            c2.conn.close()
            c3.conn.close()

        self.loop.run_until_complete(go())

    def test_pool_too_big(self):

        async def go():
            pool1 = Pool(url="ws://localhost:8182/",
                         maxsize=2,
                         username="stephen",
                         password="password",
                         future_class=Future)
            pool2 = Pool(url="ws://localhost:8182/",
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
            pool1.release(conn1)
            self.assertTrue(conn1.closed)

        self.loop.run_until_complete(go())

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
            self.assertTrue(c2.conn.closed)
            self.assertFalse(c1.conn.closed)
            c1.close()

        self.loop.run_until_complete(go())

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
            self.assertTrue(c3.cancelled())
            c1.close()
            c2.close()

        self.loop.run_until_complete(go())

class AsyncioCtxtMngrTest(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.get_event_loop()

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

        self.loop.run_until_complete(go())

    # def test_pool_manager_async_with(self):
    #     pool = Pool(url="ws://localhost:8182/",
    #                 maxsize=2,
    #                 username="stephen",
    #                 password="password",
    #                 loop=self.loop,
    #                 future_class=Future)
    #
    #     async def go():
    #         async with pool as conn:
    #             self.assertFalse(conn.closed)
    #         self.assertEqual(len(pool.pool), 1)
    #         self.assertEqual(len(pool._acquired), 0)
    #         pool.close()
    #     self.loop.run_until_complete(go())

    def test_graph_manager(self):
        graph = GraphDatabase(url="ws://localhost:8182/",
                              username="stephen",
                              password="password",
                              loop=self.loop,
                              future_class=Future)

        async def go():
            with await graph as conn:
                self.assertFalse(conn.closed)

        self.loop.run_until_complete(go())

    def test_pool_enter_runtime_error(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    future_class=Future)
        with self.assertRaises(RuntimeError):
            with pool as conn:
                self.assertFalse(conn.closed)

    def test_conn_enter_runtime_error(self):
        graph = GraphDatabase(url="ws://localhost:8182/",
                                username="stephen",
                                password="password",
                                future_class=Future)
        with self.assertRaises(RuntimeError):
            with graph as conn:
                self.assertFalse(conn.closed)


class AsyncioCallbackStyleTest(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.get_event_loop()

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
                stream = conn.send(script)
                future.set_result(stream)

            future_conn.add_done_callback(cb)

            return future

        async def go():
            result = await execute("1 + 1")
            self.assertIsInstance(result, Stream)
            resp = await result.read()
            self.assertEqual(resp.data[0], 2)

        self.loop.run_until_complete(go())


class AsyncioSessionTest(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.graph = GraphDatabase("ws://localhost:8182/",
                                   username="stephen",
                                   password="password",
                                   future_class=Future)

    def test_manual_session(self):

        async def go():
            session = await self.graph.connect(session=str(uuid.uuid4()))
            stream = session.send("v = 1+1", processor="session")
            resp = await stream.read()
            stream = session.send("v", processor="session")
            resp2 = await stream.read()
            self.assertEqual(resp.data[0], resp2.data[0])
            session.close()

        self.loop.run_until_complete(go())

    def test_no_session(self):

        async def go():
            session = await self.graph.connect()
            with self.assertRaises(RuntimeError):
                stream = session.send("v = 1+1", processor="session")

        self.loop.run_until_complete(go())

    def test_session_obj_session(self):

        async def go():
            session = await self.graph.session()
            stream = session.send("v = 1+1")
            resp = await stream.read()
            stream = session.send("v")
            resp2 = await stream.read()
            self.assertEqual(resp.data[0], resp2.data[0])

        self.loop.run_until_complete(go())


class AsyncioAPITests(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.get_event_loop()

    def test_create_connection(self):

        async def go():
            conn = await create_connection(
                "ws://localhost:8182/", password="password",
                username="stephen", loop=self.loop, future_class=Future)
            self.assertFalse(conn.conn.closed)
            conn.close()

        self.loop.run_until_complete(go())


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

        self.loop.run_until_complete(go())

    def test_script_exception(self):

        async def go():
            with self.assertRaises(RuntimeError):
                stream = await submit("ws://localhost:8182/",
                                      "throw new Exception('error')",
                                      password="password", username="stephen",
                                      loop=self.loop, future_class=Future)
                await stream.read()

        self.loop.run_until_complete(go())



if __name__ == "__main__":
    unittest.main()
