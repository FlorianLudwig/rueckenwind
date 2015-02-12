from collections import namedtuple

import pytest
import tornado.testing

import rw.scope
import rw.http
import rw.routing

from .common import generate_handler_func

## TODO
# def test_duplicated_functions():
#     m = rw.http.Module('test')
#
#     @m.get('/')
#     def foo():
#         pass
#
#     with pytest.raises(rw.routing.DuplicateError):
#         @m.get('/something_else')
#         def foo():
#             pass


class HTTPTest(tornado.testing.AsyncTestCase):
    def test_http(self):
        self.scope = rw.scope.Scope()
        with self.scope():
            self.scope.activate(rw.routing.plugin, callback=self.http)
        self.wait()

    def http(self, _):
        sub = rw.http.Module('sub')
        sub_index = generate_handler_func(sub.get, '/')
        sub_fun = generate_handler_func(sub.get, '/fun', 'fun')
        sub_posts = generate_handler_func(sub.get, '/<user_name:str>/posts', 'sub_posts')

        subsub = rw.http.Module('subsub')
        subsub_index = generate_handler_func(subsub.get, '/')
        subsub_fun = generate_handler_func(subsub.get, '/fun', 'fun')
        sub.mount('/sub', subsub)

        sub2 = rw.http.Module('sub2')
        sub2_index = generate_handler_func(sub2.get, '/')

        m = rw.http.Module('test')
        index = generate_handler_func(m.get, '/')
        index_post = generate_handler_func(m.post, '/')
        index_put = generate_handler_func(m.put, '/')
        index_delete = generate_handler_func(m.delete, '/')
        user = generate_handler_func(m.get, '/user/<user_name:str>', 'user_page')
        m.mount('/sub', sub)
        m.mount('/sub2', sub2)
        routes = m.setup()

        # mock app object
        self.scope['app'] = namedtuple('Application', 'root')(m)

        ## test find_route
        assert routes.find_route('get', '/')[1] == index
        assert routes.find_route('post', '/')[1] == index_post
        assert routes.find_route('put', '/')[1] == index_put
        assert routes.find_route('delete', '/')[1] == index_delete

        assert routes.find_route('get', '/user/joe') == ('', user, {'user_name': 'joe'})

        ## test find_route for mounts
        assert routes.find_route('get', '/sub')[1] == sub_index
        assert routes.find_route('get', '/sub2')[1] == sub2_index

        ## test url_for
        assert rw.http.url_for(index) == '/'
        assert rw.http.url_for(index_post) == '/'

        assert rw.http.url_for(user, user_name='joe') == '/user/joe'

        ## test url_for within mount
        assert rw.http.url_for(sub_index) == '/sub'
        assert rw.http.url_for(sub_fun) == '/sub/fun'
        assert rw.http.url_for(sub_posts, user_name='bob') == '/sub/bob/posts'

        ## test url_for with strings
        assert rw.http.url_for('get_index') == '/'
        assert rw.http.url_for('post_index') == '/'
        assert rw.http.url_for('user_page', user_name='joe') == '/user/joe'

        ## test url_for with strings and mount prefix
        assert rw.http.url_for('sub.get_index') == '/sub'
        assert rw.http.url_for('sub.fun') == '/sub/fun'
        assert rw.http.url_for(sub_posts, user_name='bob') == '/sub/bob/posts'
        assert rw.http.url_for('sub.subsub.get_index') == '/sub/sub'

        ## test url_for with relative string
        self.scope['rw.routing.prefix'] = ''  # mock request
        assert rw.http.url_for('.get_index') == '/'
        self.scope['rw.routing.prefix'] = 'sub'  # mock request
        assert rw.http.url_for('.get_index') == '/sub'
        assert rw.http.url_for('.fun') == '/sub/fun'
        assert rw.http.url_for('.subsub.get_index') == '/sub/sub'
        assert rw.http.url_for('.subsub.fun') == '/sub/sub/fun'

        self.scope['rw.routing.prefix'] = 'sub.subsub'  # mock request
        assert rw.http.url_for('.fun') == '/sub/sub/fun'

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

        routes = m.setup()

        assert routes.find_route('get', '/')[1] == index
        assert routes.find_route('get', '/foo')[1] == sub_index
        self.stop()

    def test_mount_variables(self):
        scope = rw.scope.Scope()
        with scope():
            scope.activate(rw.routing.plugin, callback=self.mount)
        self.wait()

    def mount_variables(self, _):
        m = rw.http.Module('test')
        index = generate_handler_func(m.get, '/')

        sub = rw.http.Module('test')
        sub_index = generate_handler_func(sub.get, '/')
        m.mount('/foo/<var>', sub)

        routes = m.setup()

        assert routes.find_route('get', '/')[1] == index
        assert routes.find_route('get', '/foo/bar')[1] == sub_index
        self.stop()