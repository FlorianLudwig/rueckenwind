import tornado.testing


class AsyncHTTPTestCase(tornado.testing.AsyncHTTPTestCase):
    def get_http_server(self):
        # setup ._app before creating http server
        self._app.setup(callback=self.stop)
        self.wait()
        return super(AsyncHTTPTestCase, self).get_http_server()