from tornado import concurrent
from tornado.ioloop import IOLoop

from gremlinclient.graph import GraphDatabase


def submit(url,
           gremlin,
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
           validate_cert=False,
           future_class=None):
    """
    Submit a script to the Gremlin Server.

    :param str url: url for Gremlin Server.
    :param str gremlin: Gremlin script to submit to server.
    :param dict bindings: A mapping of bindings for Gremlin script.
    :param str lang: Language of scripts submitted to the server.
        "gremlin-groovy" by default
    :param dict rebindings: Rebind ``Graph`` and ``TraversalSource``
        objects to different variable names in the current request
    :param str op: Gremlin Server op argument. "eval" by default.
    :param str processor: Gremlin Server processor argument. "" by default.
    :param float timeout: timeout for establishing connection (optional).
        Values ``0`` or ``None`` mean no timeout
    :param str session: Session id (optional). Typically a uuid
    :param loop: If param is ``None``, `tornado.ioloop.IOLoop.current`
        is used for getting default event loop (optional)
    :param str username: Username for SASL auth
    :param str password: Password for SASL auth
    :param bool validate_cert: validate ssl certificate. False by default
    :param class future_class: type of Future - asyncio, trollius, or tornado.
        :py:class: tornado.concurrent.Future by default
    s
    :returns: :py:class:`gremlinclient.connection.Stream` object:
    """

    loop = loop or IOLoop.current()
    graph = GraphDatabase(url=url, lang=lang,
                          processor=processor,
                          timeout=timeout,
                          username=username,
                          password=password,
                          loop=loop,
                          validate_cert=validate_cert,
                          future_class=future_class)
    future_class = future_class or concurrent.Future
    future = future_class()
    future_conn = graph.connect(force_close=True)

    def on_connect(f):
        try:
            conn = f.result()
        except Exception as e:
            future.set_exception(e)
        else:
            stream = conn.submit(gremlin, bindings=bindings, lang=lang,
                                 rebindings=rebindings, op=op,
                                 processor=processor, session=session,
                                 timeout=timeout)
            future.set_result(stream)

    future_conn.add_done_callback(on_connect)

    return future


def create_connection(url, lang="gremlin-groovy", processor="",
                      timeout=None, username="", password="",
                      loop=None, validate_cert=False, session=None,
                      force_close=False, future_class=None):
    """
    Get a database connection from the Gremlin Server.

    :param str url: url for Gremlin Server.
    :param str lang: Language of scripts submitted to the server.
        "gremlin-groovy" by default
    :param str processor: Gremlin Server processor argument. "" by default.
    :param float timeout: timeout for establishing connection (optional).
        Values ``0`` or ``None`` mean no timeout
    :param str username: Username for SASL auth
    :param str password: Password for SASL auth
    :param loop: If param is ``None``, `tornado.ioloop.IOLoop.current`
        is used for getting default event loop (optional)
    :param bool validate_cert: validate ssl certificate. False by default
    :param bool force_close: force connection to close after read.
    :param class future_class: type of Future - asyncio, trollius, or tornado.
        :py:class: tornado.concurrent.Future by default
    :param str session: Session id (optional). Typically a uuid
    :returns: :py:class:`gremlinclient.connection.Connection` object:
    """
    loop = loop or IOLoop.current()
    graph = GraphDatabase(url=url, lang=lang,
                          processor=processor,
                          timeout=timeout,
                          username=username,
                          password=password,
                          loop=loop,
                          validate_cert=validate_cert,
                          future_class=future_class)
    return graph.connect(force_close=force_close)
