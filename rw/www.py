# Copyright 2012 Florian Ludwig
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

from __future__ import absolute_import
import socket

import os
import sys
import re
import random
import urlparse
import urllib
from hashlib import md5
import mimetypes
from collections import deque
import inspect
import logging
import contextlib
import functools

import pkg_resources
from tornado import stack_context
from tornado import gen, concurrent
from tornado.web import HTTPError
import tornado.websocket
import tornado.netutil
import tornado.httpserver
from jinja2 import Environment, FunctionLoader
from bson.json_util import dumps

import rw
import rw.debug
from .check import overwrite_protected, ProtectorMeta
from . import widget
from .routing import Rule
import rbus
import rbusys

from babel.support import Translations
from babel.core import Locale


COOKIE_SECRET = ''.join([chr(random.randint(1, 255)) for i in xrange(32)])
WIDGET_FILENAMES = re.compile('[a-z][a-z_0-9]*\\.py$')
LOG = logging.getLogger(__name__)


class StaticObject(unicode):
    """Object returned by static() function, mimics a unicode string

    To make tornado accept StaticObject we inherit from unicode
    but overwrite all functions of it
    """
    def __new__(cls, *args, **kwargs):
        if not 'module' in kwargs:
            kwargs['module'] = args[0]
        if not 'fname' in kwargs:
            kwargs['fname'] = args[1]
        if not 'md5sum' in kwargs:
            kwargs['md5sum'] = args[2]
        url = '/static/' + kwargs['module'] + '/' + kwargs['fname']
        if kwargs['md5sum']:
            url += '?v=' + kwargs['md5sum'][:5]
        else:
            url += '?v=ERR'
        return unicode.__new__(cls, url)  # we are a emtpy string

    def __init__(self, module, fname, md5sum=None):
        self.module = module
        self.fname = fname
        self.md5sum = md5sum  # XXX

    def get_content(self):
        # XXX we might want to look for generated/templated static files.
        return pkg_resources.resource_string(self.module, 'static/' + self.fname)

    def get_path(self):
        # XXX we might want to look for generated/templated static files.
        return pkg_resources.resource_filename(self.module, 'static/' + self.fname)


class StaticURL(object):
    def __init__(self, handler):
        if isinstance(handler, basestring):
            class fake_handler(object):
                _parents = []
            self.handler = fake_handler
            self.module = handler
        else:
            self.handler = handler
            self.module = handler._module_name
        static_url = self

        class StaticFileHandler(tornado.web.RequestHandler):
            def get(self):
                path = self.request.path
                if '..' in path:
                    raise HTTPError(403)
                data = static_url.get_content(path)
                mime_type, _ = mimetypes.guess_type(path)
                if mime_type:
                    self.set_header("Content-Type", mime_type)
                if not data:
                    data = static_url.bfs(path)
                if data:
                    self.write(data)
                else:
                    raise HTTPError(404)
        self.static_handler = StaticFileHandler

    def __call__(self, fname):
        if ':' in fname:
            module, fname = fname.split(':', 1)
            main = rw.get_module(module).www.Main
            data = main._static.get_content(fname)
        else:
            module = self.module
            data = self.get_content(fname)
        if isinstance(data, unicode):
            data = data.encode('utf-8')
        if not data:
            data = self.bfs(fname)
        md5sum = None
        if data:
            md5sum = md5(data).hexdigest()
        return StaticObject(module, fname, md5sum)

    def bfs(self, fname):
        """Breadth-first search
        """
        search = deque(self.handler._parents)
        data = None

        while search:
            next = search.popleft()
            data = next._static.search(fname)
            if isinstance(data, basestring):
                break
            else:
                assert isinstance(data, list)
                search.extend(data)
        return data

    def search(self, fname):
        data = self.get_content(fname)
        if data:
            return data
        return self.handler._parents

    def get_content(self, fname):
        try:
            raw = pkg_resources.resource_string(self.module, 'static/' + fname)
        except IOError:
            main = self.handler
            try:
                template = main.template_env.get_template('static/' + fname)
            except IOError, e:
                # we could not find the static file ourself,
                # lets go ask our parents
                for parent in main._parents:
                    try:
                        return parent._static.get_content(fname)
                    except:
                        pass
                error = IOError('File not found {0}:{1}'.format(self.module, fname))
                error.filename = fname
                raise error
            try:
                return template.render()
            except IOError, e:
                raise IOError('Not found: {2}, referenced in {0}:{1}'.format(self.module, fname, e.filename))
        return raw

        #path = self.get_path(fname, module)
        #template_path = self.get_path(fname, module, template=True)
        ## TODO warning if both exist, template and static file
        #if os.path.exists(path):
        #    return open(path).read()
        #elif os.path.exists(template_path):
        #    main = rw.get_module(module).www.Main
        #    template = main.template_env.get_template('static/' + fname)
        #    return template.render()
        #return None


def url_for(func, **args):
    return func.im_class._rw_get_path(func.im_func, args)


def urlencode(uri, **query):
    parts = list(urlparse.urlparse(uri))
    q = urlparse.parse_qs(parts[4])
    q.update(query)
    parts[4] = urllib.urlencode(q)
    return urlparse.urlunparse(parts)


def create_template_env(load_template):
    template_env = Environment(loader=FunctionLoader(load_template),
                               extensions=['jinja2.ext.loopcontrols',
                                           'jinja2.ext.i18n',
                                           widget.Widget])

    import rw
    template_env.globals['rw'] = rw
    template_env.globals['rbus'] = rbus
    # some more default functions
    template_env.globals['enumerate'] = enumerate
    template_env.globals['isinstance'] = isinstance
    template_env.globals['len'] = len
    # default types
    template_env.globals['int'] = int
    template_env.globals['str'] = str
    template_env.globals['unicode'] = unicode
    template_env.globals['list'] = list
    template_env.globals['tuple'] = tuple
    template_env.globals['dict'] = dict
    template_env.globals['set'] = set
    template_env.globals['basestring'] = basestring
    template_env.globals['urlencode'] = urlencode
    # filter
    template_env.filters['json'] = dumps
    return template_env


class TornadoMultiDict(object):
    def __init__(self, handler):
        self.handler = handler

    def __iter__(self):
        return iter(self.handler.request.arguments)

    def __len__(self):
        return len(self.handler.request.arguments)

    def __contains__(self, name):
        # We use request.arguments because get_arguments always returns a
        # value regardless of the existence of the key.
        return (name in self.handler.request.arguments)

    def getlist(self, name):
        # get_arguments by default strips whitespace from the input data,
        # so we pass strip=False to stop that in case we need to validate
        # on whitespace.
        return self.handler.get_arguments(name, strip=False)


class RequestHandlerMeta(ProtectorMeta):
    def __new__(cls, name, bases, dct):
        is_base_class = bases == (HandlerBase, )
        ret = ProtectorMeta.__new__(cls, name, bases, dct)
        if not is_base_class:
            # find template dir
            module = dct['__module__']
            module_name = sys.modules[module].__name__
            module_path = sys.modules[module].__file__
            module_path = os.path.dirname(os.path.abspath(module_path))
            ret.module_path = module_path
            ret._rw_routes = {}

            def load_template(name):
                if ':' in name:
                    module, name = name.split(':', 1)
                else:
                    module = module_name
                path = pkg_resources.resource_filename(module, 'templates/' + name)
                # if we are in debug mode we always update templates
                # otherwise we never do
                return (open(path).read().decode('utf-8'),
                        path,
                        lambda: not rw.DEBUG)
            ret.template_env = create_template_env(load_template)
            if module.endswith('.www'):
                module = module[:-4]
            if not '_module_name' in dct:
                ret._module_name = module
            static = StaticURL(ret if not is_base_class else '')
            ret._static = static

            # inheritance
            for base in bases:
                if hasattr(base, 'template_env'):
                    ret.template_env.globals.update(base.template_env.globals)

            ret.template_env.globals['static'] = static
            ret.template_env.globals['url_for'] = url_for

            # i18n - load all available translations
            # TODO translations should be per module not handler
            ret.translations = {}
            languages = []
            if os.path.exists(module_path + '/locale'):
                languages += os.listdir(module_path + '/locale')

            for lang in languages:
                ret.translations[lang] = Translations.load(module_path + '/locale',
                                                           [Locale.parse(lang)])
                ret.translations[lang.split('_')[0]] = ret.translations[lang]

            # widgets
            # XXX experimental feature, disabled for now
            """
            ret.widgets = {}
            if os.path.exists(module_path + '/widgets'):
                for fname in os.listdir(module_path + '/widgets'):
                    if WIDGET_FILENAMES.match(fname):
                        w_name = fname[:-3]
                        w_fullname = sys.modules[module].__name__
                        w_fullname += '.widgets.' + w_name
                        mod = __import__(w_fullname)
                        ret.widgets[w_name] = mod
            """

            # make sure inheritance works
            ret._parents = [base for base in bases if issubclass(base, RequestHandler)
                            and base != RequestHandler]
        else:
            ret._parents = []
        return ret


class HandlerBase(tornado.web.RequestHandler, dict):
    # mark dict functions as overwrite protected
    for func in dir(dict):
        if not func.startswith('_'):
            overwrite_protected(getattr(dict, func))

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self._transforms = []
        self.template = None
        self.base_path = ''
        self.language = rw.cfg.get('rw', {}).get('default_language', 'en')
        browser_language = self.request.headers.get('Accept-Language', '')
        if browser_language:
            self.language = self.get_closest(*browser_language.split(','))
        self['handler'] = self
        language = self.language
        if isinstance(language, basestring):
            language = self.get_closest(language)
            if language in self.translations:
                _translation = self.translations[language]
            else:
                _translation = Translations()
        self['_translation'] = _translation
        self['_locale'] = Locale(*language.split('_'))
        self.update(self.template_subglobals)

    def get(self, key, default=None):
        return dict.get(self, key, default)

    def __cmp__(self, o):
        return id(self) == id(o)
    __eq__ = __cmp__

    @classmethod
    def _rw_get_path(cls, func, values={}):
        return cls._rw_routes[func].get_path(values)

    @overwrite_protected
    def create_form(self, name, Form, db=None, **kwargs):
        self[name] = Form(**kwargs)
        if db:
            self[name].process(obj=db)
        else:
            self[name].process(TornadoMultiDict(self))
        return self[name]

    @overwrite_protected
    def get_closest(self, *locale_codes):
        """Returns the closest supported match for the given locale code."""
        for code in locale_codes:
            if not code:
                continue

            # if there are still q=0.0 values, we ignore them for now
            # and assume the browser sends them in a sane order
            q_pos = code.find(';')
            if q_pos > 0:
                code = code[:q_pos]
            code = code.replace('-', '_')
            parts = code.split('_')

            if len(parts) > 2:
                continue
            elif len(parts) == 2:
                parts[0] = parts[0].lower()
                parts[1] = parts[1].upper()
                code = parts[0] + '_' + parts[1]
            else:
                code = code.lower()
            if code in self.translations:
                return code
            if parts[0] in self.translations:  # XXX
                return parts[0]
            # no match found, return default locale
        return self.language

    @overwrite_protected
    def render_template(self, template):
        """Render template and use i18n."""
        template = self.template_env.get_template(template)
        if '_translation' in self:
            self.template_env.install_gettext_translations(self['_translation'])
        return template.render(**self)

    @overwrite_protected
    @gen.engine
    def finish(self, chunk=None, template=None):
        """Finish Controller part and begin rendering and sending template

        """
        if self.request.method.lower() == 'head':
            tornado.web.RequestHandler.finish(self, '')
        else:
            if template:
                self.template = template
            if self.template and not chunk:
                template = self.template_env.get_template(self.template)
                # XXX translations break if we yield - and we do when streaming
                # parts of the website might end up in a different language
                if '_translation' in self:
                    self.template_env.install_gettext_translations(self['_translation'])

                stream = template.stream(**self)
                parts = []
                for part in stream:
                    # if we encounter any futures we stream the request
                    if isinstance(part, gen.Future):
                        self.write(''.join(parts))
                        self.flush()
                        parts = []
                        part = yield part
                    parts.append(part)
                self.write(''.join(parts))
            tornado.web.RequestHandler.finish(self, chunk)
        # if we are in debug mode we "want" memory leaks
        # so we can preserv all information that might be needed
        # to debug a traceback
        if not rw.DEBUG:
            dict.clear(self)
            self.ui = None

    @overwrite_protected
    def send_error(self, status_code, **kwargs):
        if self._finished:
            ioloop = tornado.ioloop.IOLoop.instance()
            ioloop.handle_callback_exception(None)
            return

        if 'exc_info' in kwargs:
            if isinstance(kwargs['exc_info'][1], HTTPError):
                self.on_error(status_code)
            else:
                ioloop = tornado.ioloop.IOLoop.instance()
                ioloop.handle_callback_exception(None)
                if rw.DEBUG:
                    self.finish(self.application.get_error_html(status_code, **kwargs))
                else:
                    self.on_error(500)
        else:
            self.on_error(status_code)

    def on_error(self, status_code):
        if self['parent_handler'] and self['parent_handler'] is not self.__class__:
            parent = self['parent_handler'](self.application, self.request)
            for key, value in self.items():
                if key not in parent:
                    parent[key] = value
            parent.on_error(status_code)
        else:
            tornado.web.RequestHandler.send_error(self, status_code)


class RequestHandler(HandlerBase):
    __metaclass__ = RequestHandlerMeta


class RequestSubHandlerMeta(ProtectorMeta):
    def __new__(cls, name, bases, dct):
        ret = ProtectorMeta.__new__(cls, name, bases, dct)
        ret._rw_routes = {}
        return ret


class RequestSubHandler(HandlerBase):
    __metaclass__ = RequestSubHandlerMeta


class Main(RequestHandler):
    pass


@contextlib.contextmanager
def rh_context(handler):
    global rw_rh_context
    rw_rh_context = handler
    yield
    rw_rh_context = None


def current_handler():
    if not 'rw_rh_context' in globals():
        return None
    return rw_rh_context


class ExecuteHandler(object):
    def __init__(self, handler, func_name, arguments):
        self.handler = handler
        self.func_name = func_name
        self.arguments = arguments

    @gen.engine
    def __call__(self, futures):
        futures = [future for future in futures if isinstance(future, concurrent.Future)]
        if futures:
            yield futures
        if hasattr(self.handler, 'pre_process'):
            future = self.handler.pre_process()
            if future:
                yield future
        getattr(self.handler, self.func_name)(**self.arguments)


def generate_plugin_handler():
    class PluginHandler(RequestHandler):
        @get('/')
        def index(self):
            self.finish('plugin handler')

        if 'rw.www' in rbusys.PLUGS:
            for plug in rbusys.PLUGS['rw.www']._plugs:
                name = plug.name
                if not name.startswith('/'):
                    name = '/' + name
                locals()[name.replace('/', '')] = mount(name, plug.handler)

    return PluginHandler


class Module(object):
    def setup(self, app_name, port, address=None):
        root_handler = rw.get_module(app_name, 'www').www.Main

        # default plugins
        import rbusys
        if isinstance(rbus.rw.email, rbusys.StubImplementation):
            log = 'No E-Mail plugin loaded -'
            if rw.DEBUG:
                from rw.plugins import mail_local as mail
                log += 'fake mail_local plugin loaded'
            else:
                from rw.plugins import mail_smtp as mail
                log += 'SMTP mail plugin loaded'
            LOG.info(log)
            mail.activate()
        if rw.DEBUG:
            from rw.plugins import debugger
            LOG.info('activate debugger')
            debugger.activate()

        base_cls = rw.debug.DebugApplication if rw.DEBUG else tornado.web.Application

        # add plugin handler
        plugin_handler = generate_plugin_handler()
        root_handler._p = mount('/_p', plugin_handler)
        routes = generate_routing(root_handler)

        class Application(base_cls):
            def __init__(self, base):
                super(Application, self).__init__(cookie_secret=COOKIE_SECRET)
                self.base = base
                self.base._rw_app = self

            @gen.engine
            def __call__(self, request):
                transforms = [t(request) for t in self.transforms]
                request.original_path = request.path
                # werzeug debugger
                found = False
                if rw.DEBUG and '__debugger__' in request.uri:
                    handler = rw.debug.WSGIHandler(self, request, rw.debug.DEBUG_APP)
                    handler.delegate()
                    handler.finish()
                    found = True
                elif request.path.startswith('/static/'):
                    path = request.path[8:].strip('/')  # len('/static/') = 8
                    path = urllib.unquote(path)
                    if '/' in path:
                        module, path = path.split('/', 1)
                        request.path = path
                        if module in sys.modules:
                            main = rw.get_module(module, 'www', auto_load=False).www.Main
                            handler = main._static.static_handler(self, request)
                            handler._execute(transforms)
                            found = True
                else:  # "normal" request
                    request.path = request.path.rstrip('/')
                    if request.path == '':
                        request.path = '/'

                    method = request.method.lower()
                    if method == 'head':
                        method = 'get'

                    for rule in routes[method]:
                        match = rule.match(request)
                        if match:
                            handler, func_name, arguments = match
                            handler = handler(self, request)
                            # tornado sets transforms in handler._execute but we are not using _execute
                            # so we need to set it here
                            handler._transforms = transforms
                            with stack_context.ExceptionStackContext(handler._stack_context_handle_exception):
                                with stack_context.StackContext(functools.partial(rh_context, handler)):
                                    preprocessors = rbus.rw.request_handling.pre_process(handler)
                                    e = ExecuteHandler(handler, func_name, arguments)
                                    e(preprocessors)
                            found = True
                            break

                if not found:
                    LOG.info('No handler found for ' + request.path)
                    self.base(self, request).send_error(404)

        app = Application(root_handler)
        app.rw_routes = routes
        if not address:
            address = '127.0.0.1' if rw.DEBUG else '0.0.0.0'

        # bind socket
        max_buffer_size = rw.cfg.get('httpserver', {}).get('max_buffer_size', 104857600)
        max_buffer_size = int(max_buffer_size)
        self.httpserver = tornado.httpserver.HTTPServer(app)
        sockets = None
        if isinstance(port, basestring):
            # If our port is a string and ends on a plus sign we
            # are searching for a free port starting from the given port
            if port.endswith('+'):
                port = port.strip('+ ')
                port = int(port)
                while port < 65536:
                    try:
                        sockets = tornado.netutil.bind_sockets(port)
                        break
                    except socket.error:
                        port += 1

        if not sockets:
            port = int(port)
            sockets = tornado.netutil.bind_sockets(port)
        self.httpserver.add_sockets(sockets)

        # save state in rw.cfg
        rw.cfg.setdefault('rw', {})
        rw.cfg['rw'].setdefault('www', {})
        rw.cfg['rw']['www'].setdefault('modules', {})
        rw.cfg['rw']['www']['modules'][app_name] = {
            'port': port,
            'address': address,
            'root_handler': root_handler
        }

        listening = 'http://{}:{}'.format(address, port)
        rw.cfg.setdefault(app_name, {})
        if not 'rw.www.base_url' in rw.cfg[app_name]:
            rw.cfg.setdefault(app_name, {}).setdefault('rw.www', {})
            rw.cfg[app_name]['rw.www']['base_url'] = listening
        else:
            rw.cfg[app_name]['rw.www']['base_url'] = rw.cfg[app_name]['rw.www']['base_url'].rstrip('/')

        LOG.info('Listening on ' + listening)
        app.base._rw_port = port

    def shutdown(self):
        self.httpserver.stop()
        del self.httpserver


def generate_routing(root):
    """generate routing "table"
    """
    ret = {}
    for req_type in ('get', 'post', 'put', 'delete', 'options'):
        ret[req_type] = _generate_routing(root, root, None, root, req_type)
    return ret


def _generate_routing(root, handler, parent, main_handler, req_type, prefix=''):
    """recursively generate routing

    main_handler is the last visited RequestHanlder in the tree
    """
    if issubclass(handler, RequestHandler):
        main_handler = handler
    else:
        handler.template_env = main_handler.template_env
        handler.translations = main_handler.translations
        handler._static = main_handler._static
    if not hasattr(handler, 'template_subglobals'):
        handler.template_subglobals = {}
    handler.template_subglobals.update({
        'main_handler': main_handler,
        'parent_handler': parent,
        'root_handler': root
    })
    ret = []
    for key, value in inspect.getmembers(handler):
        if isinstance(value, mount):
            route = prefix + value._rw_route
            if value._rw_mod is None:
                raise AttributeError('Faulty mount in {} {}'.format(handler, route))
            ret.extend(_generate_routing(root, value._rw_mod, handler, main_handler, req_type, route))
        elif hasattr(value, '_rw_route'):
            if not hasattr(value, '_rw_route_type') or value._rw_route_type != req_type:
                continue
            # generate route and normalize ending slashes
            route = (prefix + value._rw_route).rstrip('/')
            if route == '':
                route = '/'
            # we may not use direct access to value.route
            # as this will fail on methods
            route_rule = Rule(route, handler, key)
            # value.__dict__['route_rule'] = route_rule
            handler._rw_routes[value.im_func] = route_rule
            ret.append(route_rule)
    ret.sort(reverse=True)
    return ret


def get(path):
    """Expose a function for HTTP GET requests

    Example usage::

        @get('/')
        def index(self):
            ...
    """
    def wrapper(f):
        assert not hasattr(f, 'route')
        f._rw_route = path
        f._rw_route_type = 'get'
        return f
    return wrapper


def post(path):
    """Expose a function for HTTP POST requests

    Example usage::

        @post('/save')
        def save(self):
            ...
    """
    def wrapper(f):
        assert not hasattr(f, 'route')
        f._rw_route = path
        f._rw_route_type = 'post'
        return f
    return wrapper


def put(path):
    """Expose a function for HTTP PUT requests

    Example usage::

        @put('/elements/<name>')
        def save(self, name):
            ...
    """
    def wrapper(f):
        assert not hasattr(f, 'route')
        f._rw_route = path
        f._rw_route_type = 'put'
        return f
    return wrapper


def delete(path):
    """Expose a function for HTTP DELETE requests

    Example usage::

        @delete('/elements/<name>')
        def delete(self, name):
            ...
    """
    def wrapper(f):
        assert not hasattr(f, 'route')
        f._rw_route = path
        f._rw_route_type = 'delete'
        return f
    return wrapper


def options(path):
    """Expose a function for HTTP OPTIONS requests

    Example usage::

        @options('/')
        def server_options(self, name):
            ...
    """
    def wrapper(f):
        assert not hasattr(f, 'route')
        f._rw_route = path
        f._rw_route_type = 'options'
        return f
    return wrapper


class mount(object):
    def __init__(self, route, mod):
        self._rw_route = route
        self._rw_mod = mod

    def __getattr__(self, item):
        return getattr(self._rw_mod, item)


class Widget(object):
    pass


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    _rw_routes = {}  # really bad idea (only one websocket works now)

    @get('/')
    def index(self):
        self._execute([])
