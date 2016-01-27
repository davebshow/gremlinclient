# These context managers can be used for yielding active connections
# will have to do checks in yield definition, e.g. if PYTHON_34 etc.
# This is inspired by:
# https://github.com/aio-libs/aioredis/blob/master/aioredis/pool.py


class _PoolConnectionContextManager(object):

    __slots__ = ('_pool', '_conn')

    def __init__(self, pool, conn):
        self._pool = pool
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, exc_type, exc_value, tb):
        try:
            self._pool.release(self._conn.result())
        finally:
            self._pool = None
            self._conn = None


class _FactoryConnectionContextManager(object):
    __slots__ = ('_conn')

    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, exc_type, exc_value, tb):
        try:
            self._conn.result().close()
        finally:
            self._conn = None
