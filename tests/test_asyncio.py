import unittest
import asyncio

from tornado.websocket import WebSocketClientConnection
from tornado.platform.asyncio import AsyncIOMainLoop
from gremlinclient import aiosubmit



class AsyncioSyntaxTest(unittest.TestCase):

    def setUp(self):
        AsyncIOMainLoop().install()
        self.loop = asyncio.get_event_loop()

    def tearDown(self):
        AsyncIOMainLoop().clear_instance()

    def test_submit(self):

        @asyncio.coroutine
        def go():
            f = aiosubmit("1 + 1")
            resp = yield from f
            while True:
                msg = resp.read()
                msg = yield from msg
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)

        result = self.loop.run_until_complete(go())

    def test_add_handler(self):

        class Dummy(object):
            def __init__(self):
                self.results = None

            def req(self):
                future = asyncio.Future()
                future_results = aiosubmit("1 + 1")

                def process_results(results):
                    self.results = results.data
                    return results

                def set_processor(f):
                    result = f.result()
                    result.add_handler(process_results)
                    future.set_result(result)

                future_results.add_done_callback(set_processor)

                return future

        @asyncio.coroutine
        def go():
            dummy = Dummy()
            resp = yield from dummy.req()
            while True:
                msg = yield from resp.read()
                if msg is None:
                    break
                self.assertEqual(dummy.results, msg.data)

        self.loop.run_until_complete(go())


    def test_pass_handler(self):

        class Dummy(object):
            def __init__(self):
                self.results = None

            def req(self, cond):

                def process_results(results):
                    if not cond:
                        self.results = results.data
                    return results

                future_results = aiosubmit("1 + 1", handler=process_results)

                return future_results

        @asyncio.coroutine
        def go():
            dummy = Dummy()
            resp = yield from dummy.req(False)
            while True:
                msg = yield from resp.read()
                if msg is None:
                    break
                self.assertEqual(dummy.results, msg.data)

        self.loop.run_until_complete(go())


if __name__ == "__main__":
    unittest.main()
