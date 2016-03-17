SSL with :py:mod:`gremlinclient`
=================================

Setting up SSL with :py:mod:`gremlinclient` is straightforward, but different
depending on which client you choose. The following demonstrates using SSL with
both the :py:mod:`aiohttp_client<gremlinclient.aiohttp_client.client>`
and :py:mod:`tornado_client<gremlinclient.tornado_client.client>`
modules.

While SSL certs and server config are generally up to the user, but for testing
you can get going with `OpenSSL`_ self-signed certificates. Something like::

    $ openssl req -nodes -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days XXX

Then add something like this to the `conf/gremlin-server.yaml` file::

    ssl: {
      enabled: true,
      keyCertChainFile: /path/to/cert.pem,
      keyFile: /path/to/key.pem}


Okay, both `aiohttp`_ and `Tornado`_ use Python's :py:mod:`ssl` module to create an
:py:class:`ssl.SSLContext`::

    >>> import ssl
    >>> sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    >>> sslcontext.load_cert_chain(
    ...     '/path/to/cert.pem', keyfile='/path/to/key.pem')


:py:mod:`aiohttp_client<gremlinclient.aiohttp_client.client>`
-------------------------------------------------------------

To set up SSL with :py:mod:`aiohttp_client<gremlinclient.aiohttp_client.client>`,
use the :py:class:`aiohttp.TCPConnector` class::

    >>> connector = aiohttp.TCPConnector(ssl_context=sslcontext)

Then pass this object as a kwarg to
:py:func:`submit<gremlinclient.aiohttp_client.client.submit>`,
:py:func:`create_connection<gremlinclient.aiohttp_client.client.create_connection>`,
:py:class:`GraphDatabase<gremlinclient.aiohttp_client.client.GraphDatabase>`,
or :py:class:`Pool<gremlinclient.aiohttp_client.client.Pool>`::

    >>> stream = yield from submit(
    ...     "wss://localhost:8182/", "1 + 1", connector=connector)

Don't forget to use the "wss" protocol.

:py:mod:`tornado_client<gremlinclient.tornado_client.client>`
-------------------------------------------------------------

To set up SSL with :py:mod:`tornado_client<gremlinclient.tornado_client.client>`,
we create a :py:func:`request_factory` that creates
:py:class:`HTTPRequest<tornado.httpclient.HTTPRequest>` objects with the
:py:class:`ssl.SSLContext` as a frozen kwarg::

    >>> from functools import partial
    >>> request_factory = partial(
    ...     httpclient.HTTPRequest, ssl_options=sslcontext)

Then pass this object as a kwarg to
:py:func:`submit<gremlinclient.tornado_client.client.submit>`,
:py:func:`create_connection<gremlinclient.tornado_client.client>`,
:py:class:`GraphDatabase<gremlinclient.tornado_client.client.GraphDatabase>`,
or :py:class:`Pool<gremlinclient.tornado_client.client.Pool>`::

    >>> stream = yield from submit(
    ...     "wss://localhost:8182/", "1 + 1", request_factory=request_factory)

Again, don't forget to use the "wss" protocol.

.. _`aiohttp`: http://aiohttp.readthedocs.org/en/stable/client.html#ssl-control-for-tcp-sockets
.. _`OpenSSL`: https://www.openssl.org/
.. _`tornado`: http://www.tornadoweb.org/en/stable/httpclient.html#request-objects
