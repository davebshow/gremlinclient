import uuid
import unittest

from gremlinclient import Stream
from gremlinclient.requests import (
    GraphDatabase, Pool, Response)


class AsyncioFactoryConnectTest(unittest.TestCase):

    def setUp(self):
        self.graph = GraphDatabase("http://localhost:8182/",
                                   username="stephen",
                                   password="password")

    def tearDown(self):
        self.graph.close()

    def test_send(self):
        connection = self.graph.connect().result()
        resp = connection.send("1 + 1")
        msg = resp.read().result()
        self.assertEqual(msg.status_code, 200)
        self.assertEqual(msg.data[0], 2)
