def _submit(url,
            gremlin,
            graph,
            bindings=None,
            lang="gremlin-groovy",
            aliases=None,
            op="eval",
            processor="",
            timeout=None,
            session=None,
            loop=None,
            username="",
            password="",
            future_class=None):
    """
    Submit a script to the Gremlin Server.

    :param str url: url for Gremlin Server.
    :param str gremlin: Gremlin script to submit to server.
    :param class graph: GraphDatabase object used to make connection.
    :param dict bindings: A mapping of bindings for Gremlin script.
    :param str lang: Language of scripts submitted to the server.
        "gremlin-groovy" by default
    :param dict aliases: Rebind ``Graph`` and ``TraversalSource``
        objects to different variable names in the current request
    :param str op: Gremlin Server op argument. "eval" by default.
    :param str processor: Gremlin Server processor argument. "" by default.
    :param float timeout: timeout for establishing connection (optional).
        Values ``0`` or ``None`` mean no timeout
    :param str session: Session id (optional). Typically a uuid
    :param loop: If param is ``None``, :py:meth:`tornado.ioloop.IOLoop.current`
        is used for getting default event loop (optional)
    :param str username: Username for SASL auth
    :param str password: Password for SASL auth
    :param class future_class: type of Future -
        :py:class:`asyncio.Future`, :py:class:`trollius.Future`, or
        :py:class:`tornado.concurrent.Future`

    :returns: :py:class:`gremlinclient.connection.Stream` object:
    """
    future_class = graph.future_class
    future = future_class()
    future_conn = graph.connect(force_close=True)

    def on_connect(f):
        try:
            conn = f.result()
        except Exception as e:
            future.set_exception(e)
        else:
            stream = conn.send(gremlin, bindings=bindings, lang=lang,
                               aliases=aliases, op=op, processor=processor,
                               session=session, timeout=timeout)
            future.set_result(stream)

    future_conn.add_done_callback(on_connect)

    return future


def _create_connection(url, graph, timeout=None, username="", password="",
                       loop=None, session=None, force_close=False,
                       future_class=None):
    """
    Get a database connection from the Gremlin Server.

    :param str url: url for Gremlin Server.
    :param class graph: GraphDatabase object used to make connection.
    :param float timeout: timeout for establishing connection (optional).
        Values ``0`` or ``None`` mean no timeout
    :param str username: Username for SASL auth
    :param str password: Password for SASL auth
    :param loop: If param is ``None``, :py:meth:`tornado.ioloop.IOLoop.current`
        is used for getting default event loop (optional)
    :param bool force_close: force connection to close after read.
    :param class future_class: type of Future -
        :py:class:`asyncio.Future`, :py:class:`trollius.Future`, or
        :py:class:`tornado.concurrent.Future`
    :param str session: Session id (optional). Typically a uuid
    :returns: :py:class:`gremlinclient.connection.Connection` object:
    """
    return graph.connect(force_close=force_close)
