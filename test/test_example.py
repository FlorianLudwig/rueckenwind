import imp

import pkg_resources
import rw.testing

from . import example


class HTTPServerTest(rw.testing.AsyncHTTPTestCase):
    def get_app(self):
        return rw.httpbase.Application(root=imp.reload(example).root)

    def check_path(self, path, response_body=None, code=200,
                   method='GET', request_body=None):
        response = self.fetch(path, method=method, body=request_body)
        assert response.code == code
        if response_body is not None:
            assert response.body.decode('utf-8') == response_body
        return response

    def test_basic_routing(self):
        self.check_path('/', u'Hello World')
        self.check_path('/lazy', u'Hello lazy rw.http')
        self.check_path('/otherplace', u'other')
        self.check_path('/user/me', u'Hello me')
        self.check_path('/user/you', u'Hello you')
        self.check_path('/nowhere', code=404)
        self.check_path('/put', code=404)

    def test_return(self):
        self.check_path('/hello_handler', u'Hello Handler!')

    def test_template(self):
        response = self.fetch('/foo')
        assert response.code == 200
        var, hello_world, hello_world2 = response.body.decode('utf-8').strip().split('\n')
        assert var == u'static_value: 42 == 42'

        hello_world_content = pkg_resources.resource_string(
            'test.example', 'static/test.example/hello_world.txt')

        hello_world_content = hello_world_content.decode('utf-8')
        self.check_path(hello_world, hello_world_content)
        self.check_path(hello_world2, hello_world_content)
        hello_world_response = self.fetch(hello_world)

    def test_different_methods(self):
        self.check_path('/', u'root POST', method='POST', request_body='')
        self.check_path('/put', u'put', method='PUT', request_body='')
        self.check_path('/delete', u'delete', method='DELETE')
        self.check_path('/options', u'options', method='OPTIONS')

    def test_mount_tornado_handler(self):
        self.check_path('/tornado', u'Tornado GET')

    def test_static(self):
        # from static folder
        base_url = '/static/hash/test.example/'
        self.check_path(base_url + 'hello_world.txt', u'Hello Static World')

        # from static2 folder
        self.check_path(base_url + 'hallo_welt.txt', u'Guten Tag.')

        # from static2 folder (higher in config file)
        self.check_path(base_url + 'overwrite.txt', u'Overwrite')

    def test_url_for_inside_submodule(self):
        self.check_path('/sub', '/sub\n/sub')
