import json
import tornado.ioloop
import tornado.web

from tornado import gen

from gremlinclient import submit


class MainHandler(tornado.web.RequestHandler):

    @gen.coroutine
    def get(self):
        results = []
        resp = yield submit("1 + 1")
        while True:
            msg = yield resp.read()
            if msg is None:
                break
            results.append(msg.data)
        self.write(json.dumps(results))

if __name__ == "__main__":
    application = tornado.web.Application([
        (r"/", MainHandler),
    ])
    application.listen(8888)
    tornado.ioloop.IOLoop.current().start()
