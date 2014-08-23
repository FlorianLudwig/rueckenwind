import rw.testing

from . import example


class HTTPServerTest(rw.testing.AsyncHTTPTestCase):
    def get_app(self):
        return rw.httpbase.Application(root=example.root)

    def test_basic_routing(self):
        response = self.fetch('/')
        assert response.code == 200
        assert response.body.decode('utf-8') == u'Hello rw.http'

        response = self.fetch('/otherplace')
        assert response.code == 200
        assert response.body.decode('utf-8') == u'other'

        response = self.fetch('/user/me')
        assert response.code == 200
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

    def test_mount_tornado_handler(self):
        response = self.fetch('/tornado', method='GET')
        assert response.body.decode('utf-8') == u'Tornado GET'
