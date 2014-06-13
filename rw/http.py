import tornado.web

from . import scope, routing


class Module(object):
    def __init__(self, name):
        self.name = name
        self.routes = routing.RoutingTable()

    def setup(self):
        self.routes.setup()

    def _handle_request(self, handler):
        """called by RequestHandler"""
        request_scope = scope.Scope()
        request_scope['handler'] = handler
        fn, args = self.routes.find_route(handler.request.method, handler.request.path)
        if fn is None:
            raise tornado.web.HTTPError(404)
        # parse arguments?
        with request_scope():
            fn(**args)

    def get(self, path):
        """Expose a function for HTTP GET requests

        Example usage::

            @mod.get('/')
            def index(handler):
                ...
        """
        def wrapper(fn):
            fn = scope.inject(fn)
            self.routes.add_route('get', path, fn)
            return fn
        return wrapper

    def post(self, path):
        """Expose a function for HTTP POST requests

        Example usage::

            @post('/save')
            def save(self):
                ...
        """
        def wrapper(fn):
            fn = scope.inject(fn)
            self.routes.add_route('post', path, fn)
            return fn
        return wrapper

    def put(self, path):
        """Expose a function for HTTP PUT requests

        Example usage::

            @put('/elements/<name>')
            def save(self, name):
                ...
        """
        def wrapper(fn):
            fn = scope.inject(fn)
            self.routes.add_route('put', path, fn)
            return fn
        return wrapper

    def delete(self, path):
        """Expose a function for HTTP DELETE requests

        Example usage::

            @delete('/elements/<name>')
            def delete(self, name):
                ...
        """
        def wrapper(fn):
            fn = scope.inject(fn)
            self.routes.add_route('delete', path, fn)
            return fn
        return wrapper

    def options(self, path):
        """Expose a function for HTTP OPTIONS requests

        Example usage::

            @options('/')
            def server_options(self, name):
                ...
        """
        def wrapper(fn):
            fn = scope.inject(fn)
            self.routes.add_route('options', path, fn)
            return fn
        return wrapper

    def mount(self, module):
        raise NotImplementedError()
        # def __init__(self, route, mod):
        #     self._rw_route = route
        #     self._rw_mod = mod
        #
        # def __getattr__(self, item):
        #     return getattr(self._rw_mod, item)


