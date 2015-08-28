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
        self.routes = []
        self.sub_rt = []
        self.sub_request_handler = []
        self.template_env = None

    def activate(self):
        ## setup rooting
        self.setup_routing()

        ## run activate of super
        return super(Module, self).activate()

    def setup_routing(self, top=True):
        # if a Module instance is created inside some python
        # module __init__ we cannot create the template env
        # at module creation as it results in the module
        # itself being imported while getting setup
        routes = rw.routing.RoutingTable(self.name)
        for args in self.routes:
            routes.add_route(*args)

        for path, module, _, _ in self.sub_rt:
            sub_routes = module.setup_routing(False)
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

    def _generate_decorator(self, method, path):
        def decorator(fn):
            fn = scope.inject(fn)
            fn.rw_route = self.routes.append((method, path, self, fn))
            return fn

        return decorator

    def get(self, path):
        """Expose a function for HTTP GET requests

        Example usage::

            @mod.get('/')
            def index(handler):
                ...
        """

        return self._generate_decorator('get', path)

    def post(self, path):
        """Expose a function for HTTP POST requests

        Example usage::

            @post('/save')
            def save(self):
                ...
        """
        return self._generate_decorator('post', path)

    def put(self, path):
        """Expose a function for HTTP PUT requests

        Example usage::

            @put('/elements/<name>')
            def save(self, name):
                ...
        """
        return self._generate_decorator('put', path)

    def delete(self, path):
        """Expose a function for HTTP DELETE requests

        Example usage::

            @delete('/elements/<name>')
            def delete(self, name):
                ...
        """
        return self._generate_decorator('delete', path)

    def options(self, path):
        """Expose a function for HTTP OPTIONS requests

        Example usage::

            @options('/')
            def server_options(self, name):
                ...
        """
        return self._generate_decorator('options', path)

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
