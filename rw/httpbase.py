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
import tornado.ioloop
from tornado import gen
from tornado import iostream
from tornado.web import HTTPError
from tornado.concurrent import is_future
from tornado.web import _has_stream_request_body

import rw.cfg
import rw.scope
import rw.routing
import rw.template
import rw.server
import rw.event


PRE_REQUEST = rw.event.Event('httpbase.pre_request')
POST_REQUEST = rw.event.Event('httpbase.post_request')


class Application(object):
    def __init__(self, handler=None, root=None, rw_settings=None):
        """rueckenwind Application to plug into tornado's httpserver.

        Either `root` or `handler` must be specified.

        :param rw.http.Module root: The root module to serve
        :param handler: The request handler (should subclass `tornado.web.RequestHandler`)
        :param extra_configs: path to alternative config file for rueckenwind
        """
        self.io_loop = tornado.ioloop.IOLoop.current()
        self.settings = {}
        self.rw_settings = {} if rw_settings is None else rw_settings
        self.root = root
        self.scope = rw.scope.Scope()
        self.scope['app'] = self
        if self.root:
            self.handler = handler if handler is not None else RequestHandler
            pkgs = [root.name]  # TODO, Breadth-first search for dependencies
            self.scope['template_env'] = rw.template.create_template_env(pkgs)
            self.scope['template_env'].globals['app'] = self
        else:
            self.handler = handler
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
        yield rw.scope.setup_app_scope(self.root.name, self.scope, self.rw_settings)
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
                    cookie_secret = open(cs_path).read().strip()
                else:
                    cs_dir = os.path.dirname(cs_path)
                    if not os.path.exists(cs_dir):
                        os.makedirs(cs_dir)
                    cookie_secret = os.urandom(32)
                    open(cs_path, 'w').write(cookie_secret)
            elif 'random' in cfg['cookie_secret'] and cfg['cookie_secret']['random']:
                cookie_secret = os.urandom(32)
            cfg['live_settings']['cookie_secret'] = cookie_secret

    def __call__(self, request):
        """Called by `tornado.httpserver.HTTPServer` to handle a request."""
        with self.scope():
            request_scope = rw.scope.Scope()
            with request_scope():
                request_handling = self._handle_request(request_scope, request)
                self.io_loop.add_future(request_handling, self._request_finished)

    @gen.coroutine
    def _handle_request(self, request_scope, request):
        handler = self.handler(self, request)
        request_scope['handler'] = handler
        yield PRE_REQUEST()
        yield handler._execute([])
        yield POST_REQUEST()

    def _request_finished(self, request_future):
        # access result to throw exceptions that might have occurred during
        # request handling
        request_future.result()

    def log_request(self, request):
        # TODO print(request)
        pass


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

    def render(self, template_name, **kwargs):
        """Render..."""
        raise NotImplementedError()

    def render_string(self, template_name, **kwargs):
        """Generate the given template with the given arguments.

        We return the generated byte string (in utf8). To generate and
        write a template as a response, use render() above.
        """
        raise NotImplementedError()

    def get_template_namespace(self):
        """Returns a dictionary to be used as the default template namespace.

        May be overridden by subclasses to add or modify values.

        The results of this method will be combined with additional
        defaults in the `tornado.template` module and keyword arguments
        to `render` or `render_string`.
        """
        raise NotImplementedError()

    def create_template_loader(self, template_path):
        """Returns a new template loader for the given path.

        May be overridden by subclasses.  By default returns a
        directory-based loader on the given path, using the
        ``autoescape`` application setting.  If a ``template_loader``
        application setting is supplied, uses that instead.
        """
        raise NotImplementedError()

    def finish(self, chunk=None):
        """Finishes this response, ending the HTTP request."""
        if self._finished:
            raise RuntimeError("finish() called twice.  May be caused "
                               "by using async operations without the "
                               "@asynchronous decorator.")

        if chunk is not None:
            self.write(chunk)

        # Automatically support ETags and add the Content-Length header if
        # we have not flushed any content yet.
        if not self._headers_written:
            if (self._status_code == 200 and
                self.request.method in ("GET", "HEAD") and
               "Etag" not in self._headers):
                self.set_etag_header()
                if self.check_etag_header():
                    self._write_buffer = []
                    self.set_status(304)
            if self._status_code == 304:
                assert not self._write_buffer, "Cannot send body with 304"
                self._clear_headers_for_304()
            elif "Content-Length" not in self._headers:
                content_length = sum(len(part) for part in self._write_buffer)
                self.set_header("Content-Length", content_length)

        if hasattr(self.request, "connection"):
            # Now that the request is finished, clear the callback we
            # set on the HTTPConnection (which would otherwise prevent the
            # garbage collection of the RequestHandler when there
            # are keepalive connections)
            self.request.connection.set_close_callback(None)

        self.flush(include_footers=True)
        self.request.finish()
        self._log()
        self._finished = True
        self.on_finish()

    # methods to investigate for overwriting
    # def locale(self):
    # def get_user_locale(self):
    # def get_browser_locale(self, default="en_US"):
    # def current_user(self):
    # def current_user(self, value):
    # def get_current_user(self):
    # def _when_complete(self, result, callback):

    @gen.coroutine
    def _execute(self, transforms, *args, **kwargs):
        """Executes this request with the given output transforms."""
        self._transforms = transforms
        try:
            if self.request.method not in self.SUPPORTED_METHODS:
                raise HTTPError(405)
            self.path_args = [self.decode_argument(arg) for arg in args]
            self.path_kwargs = dict((k, self.decode_argument(v, name=k))
                                    for (k, v) in kwargs.items())
            # If XSRF cookies are turned on, reject form submissions without
            # the proper cookie
            if self.request.method not in ("GET", "HEAD", "OPTIONS") and \
                    self.application.settings.get("xsrf_cookies"):
                self.check_xsrf_cookie()

            result = self.prepare()
            if is_future(result):
                result = yield result
            if result is not None:
                raise TypeError("Expected None, got %r" % result)
            if self._prepared_future is not None:
                # Tell the Application we've finished with prepare()
                # and are ready for the body to arrive.
                self._prepared_future.set_result(None)
            if self._finished:
                return

            if _has_stream_request_body(self.__class__):
                # In streaming mode request.body is a Future that signals
                # the body has been completely received.  The Future has no
                # result; the data has been passed to self.data_received
                # instead.
                try:
                    yield self.request.body
                except iostream.StreamClosedError:
                    return

            result = self.handle_request()
            if is_future(result):
                result = yield result
            if result is not None:
                raise TypeError("Expected None, got %r" % result)
            if self._auto_finish and not self._finished:
                self.finish()
        except Exception as e:
            self._handle_request_exception(e)
            if (self._prepared_future is not None and
                    not self._prepared_future.done()):
                # In case we failed before setting _prepared_future, do it
                # now (to unblock the HTTP server).  Note that this is not
                # in a finally block to avoid GC issues prior to Python 3.4.
                self._prepared_future.set_result(None)

    def handle_request(self):
        routing_table = rw.scope.get('rw.http')['routing_table']
        prefix, fn, args = routing_table.find_route(self.request.method, self.request.path)
        current_scope = rw.scope.get_current_scope()
        current_scope['rw.routing.prefix'] = prefix
        current_scope['url_variables'] = args

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
    # TODO: point to alternatives in doc strings

    def get_template_path(self):
        """tornado API, not available in rw"""
        raise NotImplementedError()

    def static_url(self, path, include_host=None, **kwargs):
        """tornado API, not available in rw"""
        raise NotImplementedError()

    def reverse_url(self, name, *args):
        """tornado API, not available in rw"""
        raise NotImplementedError()

    def get_login_url(self):
        """tornado API, not available in rw"""
        raise NotImplementedError()

    def _ui_module(self, name, module):
        """tornado internal method, not used in rw"""
        raise NotImplementedError()

    def _ui_method(self, method):
        """tornado internal method, not used in rw"""
        raise NotImplementedError()
