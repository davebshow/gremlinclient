import asyncio
from gremlinclient.aiohttp_client.client import Pool

try:
    from gremlin_driver import RemoteConnection, Traverser
except ImportError:
    raise ImportError("Please install gremlinpython to use RemoteConnection")


class RemoteConnection(RemoteConnection):

    def __init__(self, url, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self._pool = Pool(url, force_release=True, loop=self._loop)

    def submit(self, script_engine, script, bindings):
        results = self._loop.run_until_complete(
            self._execute(script_engine, script, bindings))
        return results

    @asyncio.coroutine
    def _execute(self, script_engine, script, bindings):
        results = []
        conn = yield from self._pool.acquire()
        stream = conn.send(script, bindings=bindings, lang=script_engine)
        while True:
            msg = yield from stream.read()
            if msg is None or msg.data is None:
                break
            for obj in msg.data:
                results.append(Traverser(obj, 1))
        return iter(results)

    def close(self):
        self._loop.run_until_complete(self._pool.close())
