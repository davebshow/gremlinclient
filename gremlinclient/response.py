class TornadoResponse(object):

    def __init__(self, conn):
        self._conn = conn

    @property
    def conn(self):
        return self._conn

    @property
    def protocol(self):
        return self._conn.protocol

    def close(self):
        self._conn.close()

    def send(self, msg, binary=True):
        self._conn.write_message(msg, binary=binary)

    def receive(self, callback=None):
        return self._conn.read_message(callback=callback)
