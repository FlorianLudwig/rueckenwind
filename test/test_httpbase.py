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
