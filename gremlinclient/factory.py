import socket
try:
    from tornado.concurrent import Future
    from tornado.httpclient import HTTPRequest, HTTPError
    from tornado.websocket import websocket_connect
except ImportError:
    print("Tornado not available.")

from gremlinclient.response import TornadoResponse


class TornadoFactory(object):

    @classmethod
    def ws_connect(cls, url, validate_cert=False):
        return cls._ws_connect(url, validate_cert)

    @staticmethod
    def _ws_connect(url, validate_cert):
        request = HTTPRequest(url, validate_cert=validate_cert  )
        future = Future()
        future_conn = websocket_connect(request)

        def on_connect(f):
            try:
                conn = f.result()
            except socket.error:
                future.set_exception(
                    RuntimeError("Could not connect to server."))
            except socket.gaierror:
                future.set_exception(
                    RuntimeError("Could not connect to server."))
            except HTTPError as e:
                future.set_exception(e)
            except Exception as e:
                future.set_exception(e)
            else:
                future.set_result(TornadoResponse(conn))

        future_conn.add_done_callback(on_connect)
        return future
