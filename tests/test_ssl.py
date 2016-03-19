import asyncio
import functools
import ssl
import unittest

import aiohttp

from tornado import httpclient
from tornado.testing import gen_test, AsyncTestCase


from gremlinclient.aiohttp_client import submit as aiosubmit
from gremlinclient.tornado_client import submit as torsubmit


# Generate files like such:
# openssl req -nodes -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days XXX
cert = "/home/davebshow/git/gremlinclient/keys/cert.pem"
key = "/home/davebshow/git/gremlinclient/keys/key.pem"
sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
sslcontext.load_cert_chain(cert, keyfile=key)


# Add this to conf/gremlin-server.yaml (with proper path)
"""
ssl: {
  enabled: true,
  keyCertChainFile: /home/davebshow/git/gremlinclient/keys/cert.pem,
  keyFile: /home/davebshow/git/gremlinclient/keys/key.pem}
"""


class AiohttpSSLTest(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

    def tearDown(self):
        self.loop.close()


    def test_submit(self):
        connector = aiohttp.TCPConnector(ssl_context=sslcontext, loop=self.loop)
        @asyncio.coroutine
        def go():
            stream = yield from aiosubmit(
                "wss://localhost:8182/", "1 + 1", password="password",
                username="stephen", loop=self.loop, connector=connector)
            while True:
                msg = yield from stream.read()
                if msg is None:
                    break
                self.assertEqual(msg.status_code, 200)
                self.assertEqual(msg.data[0], 2)

        self.loop.run_until_complete(go())


class TornadoSSLTest(AsyncTestCase):

    @gen_test
    def test_submit(self):
        request_factory = functools.partial(
            httpclient.HTTPRequest, ssl_options=sslcontext)
        stream = yield torsubmit(
            "wss://localhost:8182/", "1 + 1", password="password",
            username="stephen", connector=request_factory)
        while True:
            msg = yield stream.read()
            if msg is None:
                break
            self.assertEqual(msg.status_code, 200)
            self.assertEqual(msg.data[0], 2)
