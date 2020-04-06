from __future__ import absolute_import, division, print_function, with_statement

import os
import hashlib
import base64

import pkg_resources
import tornado.web
import types
from tornado.util import bytes_type

import rw.plugin
import rw.scope


DEV_MODE = True
STATIC_URL_CACHE = {}


class StaticHandler(tornado.web.StaticFileHandler):
    def get(self, path, include_body=True, h=None):
        if DEV_MODE:
            self.set_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.set_header('Expires', '0')
        else:
            self.set_header('max-age=2592000')  # 30 days
        return super(StaticHandler, self).get(path, include_body)

    @classmethod
    def get_absolute_path(cls, roots, path):
        """Returns the absolute location of ``path`` relative to one of
        the ``roots``.

        ``roots`` is the path configured for this `StaticFileHandler`
        (in most cases the ``static_path`` `Application` setting).
        """
        for root in roots:
            abspath = os.path.abspath(os.path.join(root, path))
            if abspath.startswith(root) and os.path.exists(abspath):
                return abspath
        # XXX TODO
        return 'file-not-found'

    def validate_absolute_path(self, roots, absolute_path):
        """Validate and return the absolute path.

        ``root`` is the configured path for the `StaticFileHandler`,
        and ``path`` is the result of `get_absolute_path`

        This is an instance method called during request processing,
        so it may raise `HTTPError` or use methods like
        `RequestHandler.redirect` (return None after redirecting to
        halt further processing).  This is where 404 errors for missing files
        are generated.
        """
        if absolute_path is None:
            raise tornado.web.HTTPError(404)

        for root in roots:

            if (absolute_path + os.path.sep).startswith(root):
                break
        else:
            raise tornado.web.HTTPError(403, "%s is not in root static directory",
                                        self.path)

        if not os.path.isfile(absolute_path):
            raise tornado.web.HTTPError(403, "%s is not a file", self.path)

        return absolute_path


def file_hash(content):
    """Generate hash for file or string and avoid strings starting with "ad"
       to workaround ad blocks being over aggressiv.

       The current implementation is based on sha256.

       :param str|FileIO content: The content to hash, either as string or as file-like object
    """
    h = hashlib.sha256()
    if isinstance(content, bytes_type):
        h.update(content)
    else:
        data = True
        while data:
            data = content.read(1024 * 1024)
            h.update(data)
    h_digest = h.digest()
    # base64url
    # | char | substitute |
    # |   +  |    -       |
    # |   /  |    _       |
    #
    result = base64.b64encode(h_digest, altchars=b'-_')
    # ensure this is a str object in 3.x
    result = result.decode('ascii')
    result = result.rstrip('=')

    if result[:2].lower() == 'ad':
        # workaround adblockers blocking everything starting with "ad"
        # by replacing the "d" with another charackter
        if result[1] == 'd':
            result = result[0] + '~' + result[2:]
        else:
            # upper case D
            result = result[0] + '.' + result[2:]

    return result


class Static(object):
    def __init__(self):
        self.handlers = []

    def __call__(self, path):
        """returns url for static path"""
        if not path.startswith('/'):
            module = rw.scope.get('module', None)
            if module is None:
                msg = 'Relative pathes are only allowed from within a request.'
                raise AttributeError(msg)

            uri = '/static/{}/{}'.format(module.name, path)
        else:
            uri = '/static' + path

        if not DEV_MODE and uri in STATIC_URL_CACHE:
            return STATIC_URL_CACHE[uri]

        for base_uri, handler_class, roots in self.handlers:
            if uri.startswith('/' + base_uri + '/'):
                path = uri[len(base_uri) + 2:]  # remove /base_uri/
                abs_path = handler_class.get_absolute_path(roots, path)
                if not abs_path:
                    raise Exception('File Not Found %s' % repr(path))
                content = handler_class.get_content(abs_path)
                if isinstance(content, types.GeneratorType):
                    try:
                        content = b''.join(content)
                    except IOError:
                        raise Exception('File Not Found %s' % repr(path))
                break
        else:
            # XXX todo: something more sensitive
            raise Exception('File Not Found %s' % repr(path))

        h = file_hash(content)[:6]
        result = '/{}/{}/{}'.format(base_uri, h, path)
        if not DEV_MODE:
            STATIC_URL_CACHE[uri] = result

        return result

    def setup(self):
        self.handlers.sort(key=lambda x: len(x[0]), reverse=True)


plugin = rw.plugin.Plugin(__name__)


@plugin.init
def init(scope, app, settings):
    """Plugin for serving static files in development mode"""
    global DEV_MODE

    cfg = settings.get('rw.static', {})
    static = Static()
    scope['static'] = static
    scope['template_env'].globals['static'] = static

    DEV_MODE = cfg.get("DEV_MODE", True)

    for base_uri, sources in cfg.items():
        if base_uri == "DEV_MODE":
            continue

        full_paths = []
        for source in sources:
            if isinstance(source, dict):
                full_path = source['path']
                full_paths.append(full_path.format(**os.environ))
                continue
            elif ',' in source:
                module_name, path = [part.strip()
                                     for part in source.split(',')]
            else:
                module_name = source
                path = 'static'
            full_path = pkg_resources.resource_filename(module_name, path)
            full_paths.append(full_path)

        app.root.mount('/' + base_uri + '/<h>/<path:path>',
                       StaticHandler, {'path': full_paths},
                       name='static_' + base_uri.replace('.', '_'))

        static.handlers.append((base_uri, StaticHandler, full_paths))
    static.setup()
