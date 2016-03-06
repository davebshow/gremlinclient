import asyncio
import uuid
import unittest

import aiohttp

from gremlinclient import Stream
from gremlinclient.aiohttp import (
    GraphDatabase, Pool, Response, submit, create_connection)



class AsyncioFactoryConnectTest(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)
        self.graph = GraphDatabase("ws://localhost:8182/",
                                   username="stephen",
                                   password="password",
                                   loop=self.loop)

    def tearDown(self):
        self.loop.close()

    def test_connect(self):

        async def go():
            connection = await self.graph.connect()
            conn = connection.conn
            self.assertFalse(conn.closed)
            self.assertIsInstance(
                conn._conn, aiohttp.websocket_client.ClientWebSocketResponse)
            await connection.close()

        self.loop.run_until_complete(go())

    def test_bad_port_exception(self):
        graph = GraphDatabase(url="ws://localhost:81/", loop=self.loop)

        async def go():
            # Need to fix all these errors
            with self.assertRaises(aiohttp.errors.ClientOSError):
                connection = await graph.connect()

        self.loop.run_until_complete(go())


    def test_wrong_protocol_exception(self):
        graph = GraphDatabase(url="wss://localhost:8182/", loop=self.loop)

        async def go():
            with self.assertRaises(aiohttp.errors.ClientOSError):
                connection = await graph.connect()

        self.loop.run_until_complete(go())

    def test_bad_host_exception(self):
        graph = GraphDatabase(url="ws://locaost:8182/", loop=self.loop)

        async def go():
            with self.assertRaises(aiohttp.errors.ClientOSError):
                connection = await graph.connect()

        self.loop.run_until_complete(go())

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
            await connection.close()

        self.loop.run_until_complete(go())

    def test_read_one_on_closed(self):

        async def go():
            connection = await self.graph.connect()
            resp = connection.send("1 + 1")
            await connection.close()
            with self.assertRaises(RuntimeError):
                msg = await resp.read()
        self.loop.run_until_complete(go())

    def test_null_read_on_closed(self):

        async def go():
            connection = await self.graph.connect()
            # build connection
            await connection.close()
            stream = Stream(connection, None, "processor", None, self.loop,
                            "stephen", "password", False, False,
                            asyncio.Future)
            with self.assertRaises(RuntimeError):
                msg = await stream.read()

        self.loop.run_until_complete(go())
#     #
#     # def test_creditials_error(self):
#     #
#     #     @asyncio.coroutine
#     #     async def go():
#     #         graph = GraphDatabase("ws://localhost:8182/",
#     #                               username="stephen",
#     #                               password="passwor",
#     #                               loop=self.loop,
#     #                               future_class=Future)
#     #         connection = await graph.connect()
#     #         resp = connection.send("1 + 1")
#     #         with self.assertRaises(RuntimeError):
#     #             msg = await resp.read()
#     #         connection.conn.close()
#     #
#     #     self.loop.run_until_complete(go())
# #
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
# #
# #
class AsyncioPoolTest(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

    def tearDown(self):
        self.loop.close()

    def test_acquire(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop)

        async def go():
            connection = await pool.acquire()
            conn = connection.conn
            self.assertFalse(conn.closed)
            self.assertIsInstance(conn, Response)
            self.assertEqual(pool.size, 1)
            self.assertTrue(connection in pool._acquired)
            connection2 = await pool.acquire()
            conn2 = connection2.conn
            self.assertFalse(conn2.closed)
            self.assertIsInstance(conn2, Response)
            self.assertEqual(pool.size, 2)
            self.assertTrue(connection2 in pool._acquired)
            await connection.close()
            await connection2.close()

        self.loop.run_until_complete(go())

    def test_acquire_send(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop)

        async def go():
            connection = await pool.acquire()
            resp = connection.send("1 + 1")
            while True:
                msg = await resp.read()
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)
            await connection.close()

        self.loop.run_until_complete(go())

    def test_maxsize(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop)

        async def go():
            c1 = await pool.acquire()
            c2 = await pool.acquire()
            c3 = pool.acquire()
            self.assertIsInstance(c3, asyncio.Future)
            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(c3, 0.1, loop=self.loop)
            await c1.close()
            await c2.close()

        self.loop.run_until_complete(go())

    def test_release(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop)

        async def go():
            self.assertEqual(len(pool.pool), 0)
            c1 = await pool.acquire()
            self.assertEqual(len(pool._acquired), 1)
            await pool.release(c1)
            self.assertEqual(len(pool.pool), 1)
            self.assertEqual(len(pool._acquired), 0)
            await c1.close()
        self.loop.run_until_complete(go())

    def test_release_acquire(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop)

        async def go():
            c1 = await pool.acquire()
            await pool.release(c1)
            c2 = await pool.acquire()
            self.assertEqual(c1, c2)
            await c2.close()

        self.loop.run_until_complete(go())

    def test_release_closed(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop)
        self.assertEqual(len(pool.pool), 0)

        async def go():
            c1 = await pool.acquire()
            self.assertEqual(len(pool._acquired), 1)
            await c1.close()
            await pool.release(c1)
            self.assertEqual(len(pool.pool), 0)
            self.assertEqual(len(pool._acquired), 0)
            await c1.close()
        self.loop.run_until_complete(go())

    def test_self_release(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    force_release=True,
                    loop=self.loop)

        async def go():
            self.assertEqual(len(pool.pool), 0)
            c1 = await pool.acquire()
            self.assertEqual(len(pool._acquired), 1)
            stream = c1.send("1 + 1")
            resp = await stream.read()
            self.assertEqual(len(pool.pool), 1)
            self.assertEqual(len(pool._acquired), 0)
            await c1.close()

        self.loop.run_until_complete(go())

    # def test_maxsize_release(self):
    #     pool = Pool(url="ws://localhost:8182/",
    #                 maxsize=2,
    #                 username="stephen",
    #                 password="password",
    #                 loop=self.loop)
    #
    #     @asyncio.coroutine
    #     async def go():
    #         c1 = await pool.acquire()
    #         c2 = await pool.acquire()
    #         c3 = pool.acquire()
    #         self.assertIsInstance(c3, asyncio.Future)
    #         # shielded_fut = asyncio.shield(c3, loop=self.loop)
    #         # try:
    #         #     await asyncio.wait_for(shielded_fut, 0.1, loop=self.loop)
    #         #     error = False
    #         # except:
    #         #     error = True
    #         # self.assertTrue(error)
    #         await pool.release(c2)
    #         c3 = await c3
    #         self.assertEqual(c2, c3)
    #         await c1.close()
    #         await c2.close()
    #         await c3.close()
    #
    #     self.loop.run_until_complete(go())

    def test_pool_too_big(self):

        async def go():
            pool1 = Pool(url="ws://localhost:8182/",
                         maxsize=2,
                         username="stephen",
                         password="password",
                         loop=self.loop)
            pool2 = Pool(url="ws://localhost:8182/",
                         username="stephen",
                         password="password",
                         loop=self.loop)
            conn1 = await pool1.acquire()
            conn2 = await pool2.acquire()
            conn3 = await pool2.acquire()
            conn4 = await pool2.acquire()
            pool1.pool.append(conn2)
            pool1.pool.append(conn3)
            pool1.pool.append(conn4)
            await pool1.release(conn1)
            self.assertTrue(conn1.closed)
            await conn1.close()
            await pool1.close()

        self.loop.run_until_complete(go())

    def test_close(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop)

        async def go():
            c1 = await pool.acquire()
            c2 = await pool.acquire()
            await pool.release(c2)
            await pool.close()
            self.assertTrue(c2.conn.closed)
            self.assertFalse(c1.conn.closed)
            await c1.close()

        self.loop.run_until_complete(go())

    def test_cancelled(self):
        pool = Pool(url="ws://localhost:8182/",
                    maxsize=2,
                    username="stephen",
                    password="password",
                    loop=self.loop)

        async def go():
            c1 = await pool.acquire()
            c2 = await pool.acquire()
            c3 = pool.acquire()
            await pool.close()
            self.assertTrue(c3.cancelled())
            await c1.close()
            await c2.close()

        self.loop.run_until_complete(go())

# class AsyncioCtxtMngrTest(unittest.TestCase):
#
#     def setUp(self):
#         self.loop = asyncio.get_event_loop()
#
#     def test_pool_manager(self):
#         pool = Pool(url="ws://localhost:8182/",
#                     maxsize=2,
#                     username="stephen",
#                     password="password",
#                     loop=self.loop)
#
#
#         async def go():
#             with (await pool) as conn:
#                 self.assertFalse(conn.closed)
#             self.assertEqual(len(pool.pool), 1)
#             self.assertEqual(len(pool._acquired), 0)
#             await pool.close()
#
#         self.loop.run_until_complete(go())
# #
# #     def test_graph_manager(self):
# #         graph = GraphDatabase(url="ws://localhost:8182/",
# #                               username="stephen",
# #                               password="password",
# #                               loop=self.loop,
# #                               future_class=Future)
# #
# #
# #         async def go():
# #             with (await graph) as conn:
# #                 self.assertFalse(conn.closed)
# #
# #         self.loop.run_until_complete(go())
# #
# #     def test_pool_enter_runtime_error(self):
# #         pool = Pool(url="ws://localhost:8182/",
# #                     maxsize=2,
# #                     username="stephen",
# #                     password="password",
# #                     future_class=Future)
# #         with self.assertRaises(RuntimeError):
# #             with pool as conn:
# #                 self.assertFalse(conn.closed)
# #
# #     def test_conn_enter_runtime_error(self):
# #         graph = GraphDatabase(url="ws://localhost:8182/",
# #                                 username="stephen",
# #                                 password="password",
# #                                 future_class=Future)
# #         with self.assertRaises(RuntimeError):
# #             with graph as conn:
# #                 self.assertFalse(conn.closed)


class AsyncioCallbackStyleTest(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

    def tearDown(self):
        self.loop.close()

    def test_data_flow(self):

        def execute(script):
            future = asyncio.Future(loop=self.loop)
            graph = GraphDatabase(url="ws://localhost:8182/",
                                  username="stephen",
                                  password="password",
                                  loop=self.loop)
            future_conn = graph.connect(force_close=True)

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
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)
        self.graph = GraphDatabase("ws://localhost:8182/",
                                   username="stephen",
                                   password="password",
                                   loop=self.loop)

    def tearDown(self):
        self.loop.close()

    def test_manual_session(self):

        async def go():
            session = await self.graph.connect(session=str(uuid.uuid4()))
            stream = session.send("v = 1+1", processor="session")
            resp = await stream.read()
            stream = session.send("v", processor="session")
            resp2 = await stream.read()
            self.assertEqual(resp.data[0], resp2.data[0])
            await session.close()

        self.loop.run_until_complete(go())

    def test_no_session(self):

        async def go():
            session = await self.graph.connect()
            try:
                with self.assertRaises(RuntimeError):
                    stream = session.send("v = 1+1", processor="session")
            finally:
                await session.close()

        self.loop.run_until_complete(go())

    def test_session_obj_session(self):

        async def go():
            session = await self.graph.session()
            stream = session.send("v = 1+1")
            resp = await stream.read()
            stream = session.send("v")
            resp2 = await stream.read()
            self.assertEqual(resp.data[0], resp2.data[0])
            await session.close()
        self.loop.run_until_complete(go())


class AsyncioAPITests(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.get_event_loop()

    def test_create_connection(self):

        async def go():
            conn = await create_connection(
                "ws://localhost:8182/", password="password",
                username="stephen", loop=self.loop)
            self.assertFalse(conn.conn.closed)
            await conn.close()

        self.loop.run_until_complete(go())


    def test_submit(self):

        async def go():
            stream = await submit(
                "ws://localhost:8182/", "1 + 1", password="password",
                username="stephen", loop=self.loop)
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
                                           password="password",
                                           username="stephen",
                                           loop=self.loop)
                await stream.read()

        self.loop.run_until_complete(go())


if __name__ == "__main__":
    unittest.main()
