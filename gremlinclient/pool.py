import asyncio
import collections

from gremlinclient.factory import GremlinFactory


class Pool(object):

    def __init__(self, factory=GremlinFactory, maxsize=10, minsize=1):
        self._factory = factory
        self._maxsize = maxsize
        self._minsize = minsize
        self._pool = collections.deque()

    def acquire(self):
        pass

    def release(self, conn):
        pass
