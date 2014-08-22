import tornado.testing

import rw.scope
import rw.http
import rw.routing


def generate_handler_func(route_func, path):
    f = lambda x: x
    return route_func(path)(f)


class HTTPTest(tornado.testing.AsyncTestCase):
    def test_http(self):
        scope = rw.scope.Scope()
        with scope():
            scope.activate(rw.routing.plugin, callback=self.http)
        self.wait()

    def http(self, _):
        m = rw.http.Module('test')
        index = generate_handler_func(m.get, '/')
        index_post = generate_handler_func(m.post, '/')
        index_put = generate_handler_func(m.put, '/')
        index_delete = generate_handler_func(m.delete, '/')
        user = generate_handler_func(m.get, '/user/<user_name:str>')
        m.setup()

        assert m.routes.find_route('get', '/')[0] == index
        assert m.routes.find_route('post', '/')[0] == index_post
        assert m.routes.find_route('put', '/')[0] == index_put
        assert m.routes.find_route('delete', '/')[0] == index_delete

        assert m.routes.find_route('get', '/user/joe') == (user, {'user_name': 'joe'})

        assert rw.http.url_for(index) == '/'
        assert rw.http.url_for(index_post) == '/'

        assert rw.http.url_for(user, user_name='joe') == '/user/joe'
        self.stop()

    def test_mount(self):
        scope = rw.scope.Scope()
        with scope():
            scope.activate(rw.routing.plugin, callback=self.mount)
        self.wait()

    def mount(self, _):
        m = rw.http.Module('test')
        index = generate_handler_func(m.get, '/')

        sub = rw.http.Module('test')
        sub_index = generate_handler_func(sub.get, '/')
        m.mount('/foo', sub)

        m.setup()

        assert m.routes.find_route('get', '/')[0] == index
        assert m.routes.find_route('get', '/foo')[0] == sub_index
        self.stop()