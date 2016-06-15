from tornado import gen
from tornado.ioloop import IOLoop
from gremlinclient.tornado_client.client import Pool

try:
    from gremlin_driver import RemoteConnection, Traverser
except ImportError:
    raise ImportError("Please install gremlinpython to use RemoteConnection")


class RemoteConnection(RemoteConnection):

    def __init__(self, url, loop=None):
        if loop is None:
            loop = IOLoop.current()
        self._loop = loop
        self._pool = Pool(url, force_release=True, loop=self._loop)

    def submit(self, script_engine, script, bindings):
        results = self._loop.run_sync(lambda:
            self._execute(script_engine, script, bindings))
        return results

    @gen.coroutine
    def _execute(self, script_engine, script, bindings):
        results = []
        conn = yield self._pool.acquire()
        stream = conn.send(script, bindings=bindings, lang=script_engine)
        while True:
            msg = yield stream.read()
            if msg is None or msg.data is None:
                break
            for obj in msg.data:
                results.append(Traverser(obj, 1))
        raise gen.Return(iter(results))

    def close(self):
        self._pool.close()
