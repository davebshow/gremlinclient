from tornado.platform.asyncio import to_asyncio_future

from gremlinclient.client import GremlinClient, GremlinResponse


class AioGremlinClient(GremlinClient):

    def __init__(self, url='ws://localhost:8182/', loop=None,
                 lang="gremlin-groovy", processor="", timeout=None,
                 username="", password=""):
        super(AioGremlinClient, self).__init__(
            url=url, loop=loop, lang=lang, processor=processor,
            timeout=timeout, username=username, password=password)
        self._response = AioGremlinResponse

    def submit(self, gremlin, bindings=None, lang=None, rebindings=None,
               op="eval", processor=None, session=None,
               timeout=None):
        f = super(AioGremlinClient, self).submit(
            gremlin, bindings=bindings, lang=lang, rebindings=rebindings,
            op=op, processor=processor, session=session, timeout=timeout)
        return to_asyncio_future(f)


class AioGremlinResponse(GremlinResponse):

    def read(self):
        f = super(AioGremlinResponse, self).read()
        return to_asyncio_future(f)


def aiosubmit(gremlin,
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

    gc = AioGremlinClient(url=url, username=username, password=password)
    try:
        future_resp = gc.submit(gremlin, bindings=bindings, lang=lang,
                                rebindings=rebindings, op=op,
                                processor=processor, session=session,
                                timeout=timeout)
        return future_resp
    finally:
        gc.close()
