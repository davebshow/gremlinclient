class Response(object):
    """
    Wrapper for Tornado websocket client connection.

    :param tornado.websocket.WebSocketClientConnection conn: The websocket
        connection
    """
    def __init__(self, conn, future_class, loop=None):
        self._conn = conn
        self._future_class = future_class
        self._loop = loop

    @property
    def conn(self):
        """
        :returns: Underlying connection.
        """
        return self._conn

    @property
    def closed(self):
        """
        :returns: Connection protocol. None if conn is closed
        """
        return self._conn.protocol is None

    def close(self):
        """
        Close underlying client connection
        """
        self._conn.close()

    def send(self, msg, binary=True):
        """
        Send a message

        :param msg: The message to be sent.
        :param bool binary: Whether or not the message is encoded as bytes.
        """
        self._conn.write_message(msg, binary=binary)

    def receive(self, callback=None):
        """
        Read a message off the websocket.
        :param callback: To be called on message read.

        :returns: :py:class:`tornado.concurrent.Future`
        """
        return self._conn.read_message(callback=callback)
