import tornado.testing

import rw.server


class AsyncHTTPTestCase(tornado.testing.AsyncHTTPTestCase):
    def get_http_server(self):
        # setup ._app before creating http server
        rw.server.start(callback=self.stop)
        self.wait()
        return super(AsyncHTTPTestCase, self).get_http_server()