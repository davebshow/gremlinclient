from tornado import concurrent
from tornado.ioloop import IOLoop

from gremlinclient.factory import GremlinFactory


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
           password="",
           handler=None,
           validate_cert=False,
           future_class=None):

    loop = loop or IOLoop.current()
    factory = GremlinFactory(url=url, lang=lang,
                             processor=processor,
                             timeout=timeout,
                             username=username,
                             password=password,
                             loop=loop,
                             validate_cert=validate_cert)
    future_class = future_class or concurrent.Future
    future = future_class()
    future_conn = factory.connect(force_close=True)

    def on_connect(f):

        try:
            conn = f.result()
        except Exception as e:
            future.set_exception(e)
        else:
            stream = conn.submit(gremlin, bindings=bindings, lang=lang,
                                 rebindings=rebindings, op=op,
                                 processor=processor, session=session,
                                 timeout=timeout, handler=handler)
            future.set_result(stream)

    future_conn.add_done_callback(on_connect)

    return future


def create_connection(url='ws://localhost:8182/', lang="gremlin-groovy",
                      processor="", timeout=None, username="", password="",
                      loop=None, validate_cert=False, force_close=False,
                      future_class=None):
    loop = loop or IOLoop.current()
    factory = GremlinFactory(url=url, lang=lang,
                             processor=processor,
                             timeout=timeout,
                             username=username,
                             password=password,
                             loop=loop,
                             validate_cert=validate_cert,
                             future_class=future_class)
    return factory.connect(force_close=force_close)
