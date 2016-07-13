import imp

import pkg_resources
import rw.testing

from . import example


class HTTPServerTest(rw.testing.AsyncHTTPTestCase):
    def get_app(self):
        settings = rw.cfg.read_configs('test.example')
        return rw.httpbase.Application(root=imp.reload(example).root, rw_settings=settings)

    def test_basic_routing(self):
        response = self.fetch('/')
        assert response.code == 200
        assert response.body.decode('utf-8') == u'Hello rw.http'

        response = self.fetch('/lazy')
        assert response.code == 200
        assert response.body.decode('utf-8') == u'Hello lazy rw.http'

        response = self.fetch('/otherplace')
        assert response.code == 200
        assert response.body.decode('utf-8') == u'other'

        response = self.fetch('/user/me')
        assert response.code == 200
        assert response.body.decode('utf-8') == u'Hello me'

        response = self.fetch('/user/you')
        assert response.code == 200
        assert response.body.decode('utf-8') == u'Hello you'

        response = self.fetch('/nowhere')
        assert response.code == 404

        response = self.fetch('/put')
        assert response.code == 404

    def test_template(self):
        response = self.fetch('/foo')
        assert response.code == 200
        var, hello_world, hello_world2 = response.body.decode('utf-8').strip().split('\n')
        assert var == u'static_value: 42 == 42'

        hello_world_content = pkg_resources.resource_string(
            'test.example', 'static/test.example/hello_world.txt')
        hello_world_response = self.fetch(hello_world)
        assert hello_world_response.code == 200
        assert hello_world_response.body == hello_world_content

        hello_world_response2 = self.fetch(hello_world2)
        assert hello_world_response2.code == 200
        assert hello_world_response2.body == hello_world_content

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

    def test_static(self):
        # from static folder
        response = self.fetch('/static/hash/test.example/hello_world.txt', method='GET')
        assert response.body.decode('utf-8') == u'Hello Static World'

        # from static2 folder
        response = self.fetch('/static/hash/test.example/hallo_welt.txt', method='GET')
        assert response.body.decode('utf-8') == u'Guten Tag.'

        # from static2 folder (higher in config file)
        response = self.fetch('/static/hash/test.example/overwrite.txt', method='GET')
        assert response.body.decode('utf-8') == u'Overwrite'

    def test_url_for_inside_submodule(self):
        response = self.fetch('/sub', method="GET")
        assert response.body.decode('utf-8') == '/sub\n/sub'
