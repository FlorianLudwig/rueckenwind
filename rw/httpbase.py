# Copyright 2015 Florian Ludwig
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from __future__ import absolute_import, division, print_function, with_statement

import os
import inspect

import tornado.web
import tornado.httpserver
import tornado.httputil
import tornado.ioloop
from tornado import gen
from tornado import iostream
from tornado.web import HTTPError
from tornado.concurrent import is_future
from tornado.web import _has_stream_request_body
import tornado.routing

import rw.cfg
import rw.scope
import rw.routing
import rw.template
import rw.server
import rw.event


PRE_REQUEST = rw.event.Event('httpbase.pre_request')
POST_REQUEST = rw.event.Event('httpbase.post_request')


class Application(tornado.routing.ReversibleRouter):
    def __init__(self, handler=None, root=None, extra_configs=None):
        """rueckenwind Application to plug into tornado's httpserver.

        Either `root` or `handler` must be specified.

        :param rw.http.Module root: The root module to serve
        :param handler: The request handler (should subclass `tornado.web.RequestHandler`)
        :param extra_configs: path to alternative config file for rueckenwind
        """
        self.settings = {}
        self.rw_settings = {}
        self.root = root
        self.scope = rw.scope.Scope()
        self.scope['app'] = self
        self.extra_configs = extra_configs
        if self.root:
            self.handler = handler if handler is not None else RequestHandler
            self.scope['settings'] = rw.cfg.read_configs(self.root.name,
                                                         self.extra_configs)

            pkgs = self.scope['settings'].get('rw.templates', {}).get('pkgs', None)
            if not pkgs:
                pkgs = [root.name]

            self.scope['template_env'] = rw.template.create_template_env(pkgs)
            self.scope['template_env'].globals['app'] = self
        else:
            self.handler = handler
            self.scope['settings'] = {}
            assert handler is not None

        self._wsgi = False  # wsgi is not supported
        # compatibility so we can mount tornado RequestHandlers
        self.ui_modules = {}
        self.ui_methods = {}
        rw.server.PHASE_CONFIGURATION.add(self.configure)

    def configure(self):
        with self.scope():
            return self._scoped_configure()

    @gen.coroutine
    def _scoped_configure(self):
        yield rw.scope.setup_app_scope(self.root.name, self.scope)
        self.rw_settings = self.scope['settings']
        cfg_rw_http = self.rw_settings.setdefault('rw.http', {})
        cfg_rw_http['live_settings'] = self.settings
        self._configure_cookie_secret()

        yield self.scope.activate(self.root)

    def _configure_cookie_secret(self):
        cfg = self.rw_settings['rw.http']
        if 'cookie_secret' in cfg:
            if 'file' in cfg['cookie_secret']:
                cs_path = cfg['cookie_secret']['file']
                cs_path = cs_path.format(**os.environ)
                if os.path.exists(cs_path):
                    cookie_secret = open(cs_path, 'rb').read().strip()
                else:
                    cs_dir = os.path.dirname(cs_path)
                    if not os.path.exists(cs_dir):
                        os.makedirs(cs_dir)
                    cookie_secret = os.urandom(32)
                    open(cs_path, 'wb').write(cookie_secret)
            elif 'random' in cfg['cookie_secret'] and cfg['cookie_secret']['random']:
                cookie_secret = os.urandom(32)
            cfg['live_settings']['cookie_secret'] = cookie_secret

    def start_request(self, server_conn, request_conn):
        """Called by `tornado.httpserver.HTTPServer` to handle a request."""
        return RequestDispatcher(self, request_conn)

    @gen.coroutine
    def _handle_request(self, request_scope, request):
        handler = self.handler(self, request)
        request_scope['handler'] = handler
        try:
            yield PRE_REQUEST()
            yield handler._execute([])
            yield POST_REQUEST()
        except Exception as e:
            # Ensure exceptions in PRE and POST_REQUEST are
            # also forwarded to the exception handler.
            # It is not just important for logging but making
            # `raise HTTPError()` in event handlers work.
            handler._transforms = []
            handler._handle_request_exception(e)

    def _request_finished(self, request_future):
        # access result to throw exceptions that might have occurred during
        # request handling
        request_future.result()

    def log_request(self, request):
        # TODO print(request)
        pass


class RequestDispatcher(tornado.httputil.HTTPMessageDelegate):
    def __init__(self, application, connection):
        self.application = application
        self.connection = connection
        self.request = None
        self.chunks = []
        self.handler_class = None
        self.handler_kwargs = None
        self.path_args = []
        self.path_kwargs = {}
        self.stream_request_body = False

    def headers_received(self, start_line, headers):
        self.request = tornado.httputil.HTTPServerRequest(
            connection=self.connection, start_line=start_line,
            headers=headers)

        if self.stream_request_body:
            self.request.body = Future()
            return self.execute()

    def data_received(self, data):
        if self.stream_request_body:
            return self.handler.data_received(data)
        else:
            self.chunks.append(data)

    def finish(self):
        if self.stream_request_body:
            self.request.body.set_result(None)
        else:
            self.request.body = b''.join(self.chunks)
            self.request._parse_body()
            self.execute()

    def on_connection_close(self):
        if self.stream_request_body:
            self.handler.on_connection_close()
        else:
            self.chunks = None

    def execute(self):
        app = self.application
        with app.scope():
            request_scope = rw.scope.Scope()
            with request_scope():
                request_handling = app._handle_request(request_scope, self.request)
                io_loop = tornado.ioloop.IOLoop.current()
                io_loop.add_future(request_handling, app._request_finished)


class RequestHandler(tornado.web.RequestHandler, dict):
    def __init__(self, application, request, **kwargs):
        # The super class is not called since it creates
        # some structures we do not care about.  Since
        # the "not caring" leads to memory leaks they
        # are not created in the first place.

        self.application = application
        self.request = request
        self._headers_written = False
        self._finished = False
        self._auto_finish = False  # vanilla tornado defaults to True
        self._transforms = None  # will be set in _execute
        self._prepared_future = None

        # variables from vanilla tornado, not avaiable in rw
        # self.path_args
        # self.path_kwargs
        # self.ui
        self.clear()
        self.request.connection.set_close_callback(self.on_connection_close)
        self.initialize(**kwargs)

    def head(self, *args, **kwargs):
        return self.handle_request()

    def get(self, *args, **kwargs):
        return self.handle_request()

    def post(self, *args, **kwargs):
        return self.handle_request()

    def delete(self, *args, **kwargs):
        return self.handle_request()

    def patch(self, *args, **kwargs):
        return self.handle_request()

    def put(self, *args, **kwargs):
        return self.handle_request()

    def options(self, *args, **kwargs):
        return self.handle_request()

    def send_error(self, status_code=500, **kwargs):
        if status_code == 500:
            handle = rw.scope.get('rw.httpbase:handle_exception', None)
            if handle:
                handle(self, kwargs)
                return

        tornado.web.RequestHandler.send_error(self, status_code, **kwargs)

    def handle_request(self):
        routing_table = rw.scope.get('rw.http')['routing_table']
        prefix, module, fn, args = routing_table.find_route(self.request.method, self.request.path)
        current_scope = rw.scope.get_current_scope()
        current_scope['rw.routing.prefix'] = prefix
        current_scope['url_variables'] = args
        current_scope['module'] = module

        if fn is None:
            raise tornado.web.HTTPError(404)

        # only supply arguments if those are "welcome"
        if hasattr(fn, '_rw_wrapped_function'):
            arg_spec = inspect.getargspec(fn._rw_wrapped_function)
        else:
            arg_spec = inspect.getargspec(fn)

        if arg_spec.keywords is not None:
            # fn accepts **keywords arguments so we pass all variables
            return fn(**args)

        call_args = {}
        for arg, value in args.items():
            if arg in arg_spec.args:
                call_args[arg] = value
        return fn(**call_args)

    # overwrite methodes that are not supported to make sure
    # they get not used by accident.

    def render(self, template_name, **kwargs):
        """tornado API, not available in rw"""
        raise NotImplementedError()

    def render_string(self, template_name, **kwargs):
        """tornado API, not available in rw"""
        raise NotImplementedError()

    def get_template_namespace(self):
        """tornado API, not available in rw"""
        raise NotImplementedError()

    def create_template_loader(self, template_path):
        """tornado API, not available in rw"""
        raise NotImplementedError()

    def get_template_path(self):
        """tornado API, not available in rw"""
        raise NotImplementedError()

    def static_url(self, path, include_host=None, **kwargs):
        """tornado API, not available in rw"""
        raise NotImplementedError()

    def reverse_url(self, name, *args):
        """tornado API, not available in rw"""
        raise NotImplementedError()

    def _ui_module(self, name, module):
        """tornado internal method, not used in rw"""
        raise NotImplementedError()

    def _ui_method(self, method):
        """tornado internal method, not used in rw"""
        raise NotImplementedError()
