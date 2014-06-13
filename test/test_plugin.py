import tornado.testing

import rw.plugin
import rw.scope


class MyTestCase(tornado.testing.AsyncTestCase):
    @tornado.testing.gen_test
    def test_basic(self):
        scope = rw.scope.Scope()

        plugin = rw.plugin.Plugin('rw.test')

        @plugin.init
        def init(scope):
            scope['foo'] = 1

        with scope():
            yield scope.activate(plugin)
            assert scope.get('foo') == 1

        # plugin.provider
        # plugin.
        # @plugin.func
        # def inc(foo):
        #     return foo + 1
        #
        # @plugin.provider
        # def inc(foo):
        #     return foo + 1


        # scope.get('inc') == inc
        # assert scope.get('inc')(1) == 2


