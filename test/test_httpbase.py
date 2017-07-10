import tornado.web
from tornado.testing import AsyncHTTPTestCase, AsyncTestCase, ExpectLog, gen_test

import rw.httpbase


class HelloWorldHandler(rw.httpbase.RequestHandler):
    def handle_request(self):
        self.finish('Hello World')


class HTTPServerTest(AsyncHTTPTestCase):
    def get_app(self):
        return rw.httpbase.Application(handler=HelloWorldHandler)

    def test_hello_world(self):
        response = self.fetch('/')
        assert response.body.decode('utf-8') == u'Hello World'


class HTTPServerEventTest(AsyncHTTPTestCase):
    def get_app(self):
        return rw.httpbase.Application(handler=HelloWorldHandler)

    def test_hello_world(self):
        rw.httpbase.PRE_REQUEST.add(self.raise_404)
        response = self.fetch('/')
        assert response.code == 404

    def raise_404(self):
        raise tornado.web.HTTPError(404)

    @classmethod
    def teardown_class(cls):
        rw.httpbase.PRE_REQUEST.clear()
