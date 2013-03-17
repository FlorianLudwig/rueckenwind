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

import pkg_resources
import tornado.websocket
from tornado.web import HTTPError
from jinja2 import Environment, FunctionLoader

import rw
from . import debug, routing, widget
import rbus
import rbusys

from babel.support import Translations
from babel.core import Locale


COOKIE_SECRET = ''.join([chr(random.randint(1, 255)) for i in xrange(32)])
WIDGET_FILENAMES = re.compile('[a-z][a-z_0-9]*\\.py$')
LOG = logging.getLogger(__name__)


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
        url = '/static/' + module + '/' + fname
        if isinstance(data, unicode):
            data = data.encode('utf-8')
        if not data:
            tag = 'ERR'
            data = self.bfs(fname)
        if data:
            tag = md5(data).hexdigest()[:4]
        return url + '?v=' + tag

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
                raise IOError('File not found {0}:{1}'.format(self.module, fname))
            try:
                return template.render()
            except IOError, e:
                raise IOError('Not found: ' + e.filename +
                              ', referenced in {0}:{1}'.format(self.module, fname))
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
    base = func.im_self.base_path
    if args:
        return base + func.route_rule.get_path(args)
    return base + func.route


def urlencode(uri, **query):
    parts = list(urlparse.urlparse(uri))
    q = urlparse.parse_qs(parts[4])
    q.update(query)
    parts[4] = urllib.urlencode(q)
    return urlparse.urlunparse(parts)


def _generate_sub_handler(path, sub_handler):
    def delegate_handler(req_handler):
        base_path = req_handler.base_path + path
        request = req_handler.request
        request.path = request.path[len(path):]
        if not request.path.startswith('/'):
            request.path = '/' + request.path
        new_handler = sub_handler(req_handler.application, request)
        new_handler.base_path = base_path
        new_handler._handle_request()

    class Obj(object):
        route = path
        route_type = '*'
    return delegate_handler, Obj


class RequestHandlerMeta(type):
    def __new__(cls, name, bases, dct):
        is_base_class = bases == (tornado.web.RequestHandler, dict)
        routes = []
        mounts = dct.get('_mounts', [])
        if '_mounts' in dct:
            del dct['_mounts']
        ret = type.__new__(cls, name, bases, dct)
        ret.routes = routes
        # find template dir
        module = dct['__module__']
        module_name = sys.modules[module].__name__
        module_path = sys.modules[module].__file__
        module_path = os.path.dirname(os.path.abspath(module_path))
        #templates_path = module_path + '/templates'
        ret.module_path = module_path
        #ret.templates_path = templates_path

        def load_template(name):
            if ':' in name:
                module, name = name.split(':', 1)
            else:
                module = module_name
            path = pkg_resources.resource_filename(module, 'templates/' + name)
            # we always update the template so we return an uptodatefunc
            # that always returns False
            return (open(path).read().decode('utf-8'),
                    path,
                    lambda: False)
        ret.template_env = Environment(loader=FunctionLoader(load_template),
                                       extensions=['jinja2.ext.loopcontrols',
                                                   'jinja2.ext.i18n',
                                                   widget.Widget])
        if module.endswith('.www'):
            module = module[:-4]
        ret._module_name = module
        static = StaticURL(ret if not is_base_class else '')
        ret._static = static
        for base in bases:
            if hasattr(base, 'template_env'):
                ret.template_env.globals.update(base.template_env.globals)

        ret.template_env.globals['static'] = static
        ret.template_env.globals['url_for'] = url_for
        ret.template_env.globals['rbus'] = rbus
        import rw
        ret.template_env.globals['rw'] = rw
        # some more default functions
        ret.template_env.globals['enumerate'] = enumerate
        #ret.template_env.globals['sorted'] = sorted
        ret.template_env.globals['isinstance'] = isinstance
        ret.template_env.globals['len'] = len
        # default types
        ret.template_env.globals['int'] = int
        ret.template_env.globals['str'] = str
        ret.template_env.globals['unicode'] = unicode
        ret.template_env.globals['list'] = list
        ret.template_env.globals['tuple'] = tuple
        ret.template_env.globals['dict'] = dict
        ret.template_env.globals['set'] = set
        ret.template_env.globals['basestring'] = basestring
        ret.template_env.globals['urlencode'] = urlencode

        # i18n - load all available translations
        if not 'language' in dct:
            ret.language = 'en'  # XXX use system default?
        ret.translations = {}
        languages = [ret.language]
        if os.path.exists(module_path + '/locale'):
            languages += os.listdir(module_path + '/locale')

        for lang in languages:
            ret.translations[lang] = Translations.load(module_path + '/locale',
                                                       [Locale.parse(lang)])
            ret.translations[lang.split('_')[0]] = ret.translations[lang]

        # widgets
        ret.widgets = {}
        if os.path.exists(module_path + '/widgets'):
            for fname in os.listdir(module_path + '/widgets'):
                if WIDGET_FILENAMES.match(fname):
                    w_name = fname[:-3]
                    w_fullname = sys.modules[module].__name__
                    w_fullname += '.widgets.' + w_name
                    mod = __import__(w_fullname)
                    ret.widgets[w_name] = mod

        # make sure inheritance works
        if not is_base_class:
            for key, obj in dct.items():
                if hasattr(obj, 'route'):
                    routes.append(routing.Rule(obj, key))
            ret._parents = [base for base in bases if issubclass(base, RequestHandler)
                            and base != RequestHandler]
        else:
            ret._parents = []
        for base in bases:
            if hasattr(base, 'routes'):
                for route in base.routes:
                    handler = route.handler
                    if handler not in [r.handler for r in routes]:
                        obj = getattr(base, handler)
                        routes.append(routing.Rule(obj, handler))
        # add mounts
        for path, sub_handler in mounts:
            delegate_handler, Obj = _generate_sub_handler(path, sub_handler)
            routes.append(routing.Rule(Obj, delegate_handler))
        routes.sort(reverse=True)
        return ret


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


class RequestHandler(tornado.web.RequestHandler, dict):
    __metaclass__ = RequestHandlerMeta

    def __init__(self, application, request, **kwargs):
        super(RequestHandler, self).__init__(application, request, **kwargs)
        self._transforms = []
        self.template = None
        self.base_path = ''
        browser_language = self.request.headers.get('Accept-Language', '')
        if browser_language:
            self.language = self.get_closest(*browser_language.split(','))
        self['handler'] = self

    def __cmp__(self, o):
        return id(self) == id(o)
    __eq__ = __cmp__

    def create_form(self, name, Form, db=None):
        self[name] = Form()
        if db:
            self[name].process(obj=db)
        else:
            self[name].process(TornadoMultiDict(self))
        return self[name]

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

    def render_template(self, template):
        """Render template and use i18n."""
        template = self.template_env.get_template(template)
        language = self.language
        if isinstance(language, basestring):
            language = self.get_closest(language)
            language = self.translations[language]
        self.template_env.install_gettext_translations(language)
        return template.render(**self)

    def finish(self, chunk=None, template=None):
        """Finish Controller part and begin rendering and sending template

        """
        if template:
            self.template = template
        if self.template and not chunk:
            self.write(self.render_template(self.template))
        super(RequestHandler, self).finish(chunk)

    def _handle_request(self):
        for rule in self.routes:
            if rule.match(self, self.request):
                return True
        return False

    def send_error(self, status_code, **kwargs):
        if 'exc_info' in kwargs:
            # TODO check self._headers_written
            ioloop = tornado.ioloop.IOLoop.instance()
            ioloop.handle_callback_exception(None)
            if not self._finished:
                self.finish(self.application.get_error_html(status_code, **kwargs))
        else:
            super(RequestHandler, self).send_error(status_code, **kwargs)


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def _handle_request(self):
        self._execute([])


class Main(RequestHandler):
    pass


def setup(app_name, address=None, port=None):
    app = rw.get_module(app_name, 'www').www.Main

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

    class Application(base_cls):
        def __init__(self, base):
            super(Application, self).__init__(cookie_secret=COOKIE_SECRET)
            self.base = base

        def __call__(self, request):
            request.original_path = request.path
            # werzeug debugger
            if rw.DEBUG and '__debugger__' in request.uri:
                handler = rw.debug.WSGIHandler(self, request, rw.debug.DEBUG_APP)
                handler.delegate()
                handler.finish()
                return
            # static file?
            if request.path.startswith('/static/'):
                path = request.path[8:].strip('/')  # len('/static/') = 8
                if '/' in path:
                    module, path = path.split('/', 1)
                    request.path = path
                    if module in sys.modules:
                        main = rw.get_module(module, 'www', auto_load=False).www.Main
                        handler = main._static.static_handler(self, request)
                        handler._execute([])
                        return
            elif request.path.startswith('/_p/'):
                path = request.path[4:]
                plugin, path = path.split('/', 1)
                mod = rbusys.PLUGS.get(plugin)
                for plug in rbusys.PLUGS['rw.www']._plugs:
                    if plug.name == plugin:
                        request.path = '/' + path
                        if plug.handler(self, request)._handle_request():
                            return
            else:  # "normal" request
                request.path = request.path.rstrip('/')
                if request.path == '':
                    request.path = '/'
                handler = self.base(self, request)
                rbus.rw.request_handling.pre_process(handler)
                if handler._handle_request():
                    return
            # TODO handle this proberly
            # raise tornado.web.HTTPError(404, "Path not found " + request.path)
            handler = tornado.web.ErrorHandler(self, request, status_code=404)
            handler._execute([])
            return handler

    app = Application(app)
    if not address:
        address = '127.0.0.1' if rw.DEBUG else '0.0.0.0'
    if not port:
        port = 9999
    LOG.info('Listening on http://%s:%i' % (address, port))
    app.listen(port, address=address)
    #path.append(os.path.dirname(os.path.abspath(sys.argv[0])))
    if rw.DEBUG:
        tornado.autoreload.start()


def get(path):
    """Expose a function for HTTP GET requests

    Example usage::

        @get('/')
        def index(self):
            ...
    """
    def wrapper(f):
        assert not hasattr(f, 'route')
        f.route = path
        f.route_type = 'GET'
        return f
    return wrapper


def post(path):
    """Expose a function for HTTP POST requests

    Example usage::

        @get('/save')
        def save(self):
            ...
    """
    def wrapper(f):
        assert not hasattr(f, 'route')
        f.route = path
        f.route_type = 'POST'
        return f
    return wrapper


def put(path):
    """Expose a function for HTTP PUT requests

    Example usage::

        @get('/elements/<name>')
        def save(self, name):
            ...
    """
    def wrapper(f):
        assert not hasattr(f, 'route')
        f.route = path
        f.route_type = 'PUT'
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
        f.route = path
        f.route_type = 'DELETE'
        return f
    return wrapper


def mount(path, mod):
    """Mount `RequestHandler` within another handler.

    Example usage::

        class A(RequestHandler):
            @get('/')
            def index(self):
                self.finish('index of A')

        class B(RequestHandler):
            mount('/a', A)
    """
    # get the locals from where our request class is constructed
    # by traveling up the interpreter stack by one frame
    frame = inspect.stack()[1][0]
    f_locals = frame.f_locals

    # add arguments, they are processed into routing rules in
    # RequestHandler.__new__
    f_locals.setdefault('_mounts', []).append((path, mod))


def load(mod):
    assert hasattr(mod, 'Main')


class Widget(object):
    pass
