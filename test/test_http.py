from tornado.testing import AsyncHTTPTestCase

import rw.http
import rw.httpbase

test = rw.http.Module(__name__)


@test.get('/')
def root(handler):
    handler.finish('Hello rw.http')


class HTTPServerTest(AsyncHTTPTestCase):
    def get_app(self):
        return rw.httpbase.Application(root=test)

    def test_hello_world(self):
        response = self.fetch('/')
        assert response.body.decode('utf-8') == u'Hello rw.http'