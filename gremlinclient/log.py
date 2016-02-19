import logging


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


connection_logger = logging.getLogger("gremlinclient.connection")
graph_logger = logging.getLogger("gremlinclient.graph")
pool_logger = logging.getLogger("gremlinclient.pool")
