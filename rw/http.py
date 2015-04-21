import inspect
import tornado.web

from . import scope

import rw.plugin
import rw.routing
import rw.template


class Module(rw.plugin.Plugin):
    def __init__(self, name, resources=None):
        super(Module, self).__init__(name)
        self.resources = name if resources is None else resources
        self.activate_event.add(self.setup)
        self.routes = []
        self.sub_rt = []
        self.sub_request_handler = []
        self.template_env = None

    def setup(self, top=True):
        # if a Module instance is created inside some python
        # module __init__ we cannot create the template env
        # at module creation as it results in the module
        # itself being imported while getting setup
        routes = rw.routing.RoutingTable(self.name)
        for args in self.routes:
            routes.add_route(*args)

        for path, module, _, _ in self.sub_rt:
            sub_routes = module.setup(False)
            routes.add_child(path, sub_routes)

        for args in self.sub_request_handler:
            routes.add_request_handler(*args)

        if top:
            routes.setup()
            current_scope = scope.get_current_scope()
            if current_scope is not None:
                current_scope.setdefault('rw.http', {})['routing_table'] = routes
        return routes

    @scope.inject
    def render_template(self, template_name, template_env, handler):
        if not template_name.startswith('/'):
            template_name = self.resources + '/' + template_name
        template = template_env.get_template(template_name)
        handler.finish(template.render(**handler))

    def get(self, path):
        """Expose a function for HTTP GET requests

        Example usage::

            @mod.get('/')
            def index(handler):
                ...
        """
        def wrapper(fn):
            fn = scope.inject(fn)
            fn.rw_route = self.routes.append(('get', path, self, fn))
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
            fn.rw_route = self.routes.append(('post', path, self, fn))
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
            fn.rw_route = self.routes.append(('put', path, self, fn))
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
            fn.rw_route = self.routes.append(('delete', path, self, fn))
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
            fn.rw_route = self.routes.append(('options', path, self, fn))
            return fn
        return wrapper

    def mount(self, path, module, handler_args=None, name=None):
        if handler_args is None:
            handler_args = {}
        if inspect.isclass(module) and issubclass(module, tornado.web.RequestHandler):
            self.sub_request_handler.append((path, module, handler_args, name))
        else:
            self.sub_rt.append((path, module, handler_args, name))


def url_for(func, **kwargs):
    if isinstance(func, str):
        if func.startswith('.'):
            # relative to current module
            routing_table = scope.get('rw.http')['routing_table']
            prefix = scope.get('rw.routing.prefix')
            path = (prefix + func).lstrip('.')
            return routing_table.get_path(path, kwargs)
        else:
            # absolute
            routing_table = scope.get('rw.http')['routing_table']
            return routing_table.get_path(func, kwargs)
    else:
        return func.rw_route.get_path(kwargs)
