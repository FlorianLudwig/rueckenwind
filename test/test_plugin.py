import tornado.testing

import rw.plugin
import rw.scope


class MyTestCase(tornado.testing.AsyncTestCase):
    def test_basic(self):
        scope = rw.scope.Scope()

        plugin = rw.plugin.Plugin('rw.test')

        @plugin.init
        def init(scope):
            scope['foo'] = 1

        with scope():
            scope.activate(plugin, callback=self.inside_scope)
        self.wait()

    @rw.scope.inject
    def inside_scope(self, result, scope):
        assert scope.get('foo') == 1
        self.stop()
