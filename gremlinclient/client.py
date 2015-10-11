import collections
import json
import uuid
from tornado.websocket import websocket_connect
from tornado.concurrent import Future
# from tornado.platform.asyncio import to_asyncio_future
#
# try:
#     import asyncio
# except ImportError:
#     import trollius as asyncio

Message = collections.namedtuple(
    "Message",
    ["status_code", "data", "message", "metadata"])


class GremlinResponseStream:

    def __init__(self, conn):
        self._conn = conn
        self._closed = False

    def read(self):
        future = Future()
        if self._closed:
            future.set_result(None)
        else:
            future_resp = self._conn.read_message()

            def parser(f):
                message = json.loads(f.result())
                message = Message(message["status"]["code"],
                                  message["result"]["data"],
                                  message["result"]["meta"],
                                  message["status"]["message"])
                if message.status_code == 200:
                    future.set_result(message)
                    self._closed = True
                elif message.status_code == 206 or message.status_code == 407:
                    future.set_result(message)
                elif message.status_code == 204:
                    future.set_result(message)
                    self._closed = True
                else:
                    future.cancel()
                    raise RuntimeError(
                        "{0} {1}".format(message.status_code, message.message))

            future_resp.add_done_callback(parser)
        return future


def submit(gremlin,
           url='ws://localhost:8182/',
           bindings=None,
           lang="gremlin-groovy",
           rebindings=None,
           op="eval",
           processor="",
           timeout=None,
           session=None,
           loop=None,
           username="",
           password=""):

    if rebindings is None:
        rebindings = {}

    message = json.dumps({
        "requestId": str(uuid.uuid4()),
        "op": op,
        "processor": processor,
        "args": {
            "gremlin": gremlin,
            "bindings": bindings,
            "language":  lang,
            "rebindings": rebindings
        }
    })
    future = Future()
    future_conn = websocket_connect(url)

    def send_message(f):
        conn = f.result()
        conn.write_message(message)
        future.set_result(GremlinResponseStream(conn))

    future_conn.add_done_callback(send_message)

    return future
