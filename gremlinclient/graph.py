import socket
import sys
import textwrap

from gremlinclient.connection import Connection, Session
from gremlinclient.response import Response


PY_33 = sys.version_info >= (3, 3)
PY_35 = sys.version_info >= (3, 5)


class GraphDatabase(object):
    """This class generates connections to the Gremlin Server.

    :param str url: url for Gremlin Server.
    :param float timeout: timeout for establishing connection (optional).
        Values ``0`` or ``None`` mean no timeout
    :param str username: Username for SASL auth
    :param str password: Password for SASL auth
    :param loop: If param is ``None``, `tornado.ioloop.IOLoop.current`
        is used for getting default event loop (optional)
    :param bool validate_cert: validate ssl certificate. False by default
    :param class future_class: type of Future -
        :py:class:`asyncio.Future`, :py:class:`trollius.Future`, or
        :py:class:`tornado.concurrent.Future`
    """

    def __init__(self, url, timeout=None, username="",
                 password="", loop=None, validate_cert=False,
                 future_class=None, session_class=Session):
        self._url = url
        self._timeout = timeout
        self._username = username
        self._password = password
        self._loop = loop
        self._validate_cert = validate_cert
        # Hmmm
        self._future_class = future_class
        self._session_class = session_class

    @property
    def future_class(self):
        return self._future_class

    def connect(self,
                session=None,
                force_close=False,
                force_release=False,
                pool=None):
        """
        Get a connection to the graph database.

        :param str session: Session id (optional). Typically a uuid
        :param bool force_close: force connection to close after read.
        :param bool force_release: If possible, force release to pool after
            read.
        :param gremlinclient.pool.Pool pool: Associated connection pool.

        :returns: :py:class:`gremlinclient.connection.Connection`
        """
        return self._connect(
            Connection, session, force_close, force_release, pool)

    def session(self,
                connector=None,
                session=None,
                force_close=False,
                force_release=False,
                pool=None):
        """
        Get a session connection to the graph database.

        :param str session: Session id (optional). Typically a uuid
        :param bool force_close: force connection to close after read.
        :param bool force_release: If possible, force release to pool after
            read.
        :param gremlinclient.pool.Pool pool: Associated connection pool.

        :returns: :py:class:`gremlinclient.connection.Session`
        """
        return self._connect(
            Session, session, force_close, force_release, pool)

    def _connect(self,
                 conn_type,
                 session,
                 force_close,
                 force_release,
                 pool):
        raise NotImplementedError
