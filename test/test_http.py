import rw.testing
import rw.http
import rw.httpbase

test = rw.http.Module(__name__)


@test.get('/')
def root(handler):
    handler.finish('Hello rw.http')


@test.post('/')
def root_submit(handler):
    handler.finish('root POST')


@test.get('/user/<name>')
def root_submit(handler, name):
    handler.finish('Hello ' + name)


@test.get('/otherplace')
def other(handler):
    handler.finish('other')


@test.put('/put')
def put(handler):
    handler.finish('put')


@test.delete('/delete')
def delete(handler):
    handler.finish('delete')


@test.options('/options')
def options(handler):
    handler.finish('options')


class HTTPServerTest(rw.testing.AsyncHTTPTestCase):
    def get_app(self):
        return rw.httpbase.Application(root=test)

    def test_basic_routing(self):
        response = self.fetch('/')
        assert response.body.decode('utf-8') == u'Hello rw.http'

        response = self.fetch('/otherplace')
        assert response.body.decode('utf-8') == u'other'

        response = self.fetch('/user/me')
        assert response.body.decode('utf-8') == u'Hello me'

        response = self.fetch('/nowhere')
        assert response.code == 404

        response = self.fetch('/put')
        assert response.code == 404

    def test_different_methods(self):
        response = self.fetch('/', method='POST', body='')
        assert response.body.decode('utf-8') == u'root POST'

        response = self.fetch('/put', method='PUT', body='')
        assert response.body.decode('utf-8') == u'put'

        response = self.fetch('/delete', method='DELETE')
        assert response.body.decode('utf-8') == u'delete'

        response = self.fetch('/options', method='OPTIONS')
        assert response.body.decode('utf-8') == u'options'

