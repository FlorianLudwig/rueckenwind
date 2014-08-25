from __future__ import absolute_import, division, print_function, with_statement

import os

import pkg_resources
import tornado.web

import rw.plugin


class StaticHandler(tornado.web.StaticFileHandler):
    @classmethod
    def get_absolute_path(self, roots, path):
        """Returns the absolute location of ``path`` relative to one of
        the ``roots``.

        ``roots`` is the path configured for this `StaticFileHandler`
        (in most cases the ``static_path`` `Application` setting).

        .. versionadded:: 3.1
        """
        for root in roots:
            abspath = os.path.abspath(os.path.join(root, path))
            if os.path.exists(abspath):
                return abspath
        return None

    def validate_absolute_path(self, roots, absolute_path):
        """Validate and return the absolute path.

        ``root`` is the configured path for the `StaticFileHandler`,
        and ``path`` is the result of `get_absolute_path`

        This is an instance method called during request processing,
        so it may raise `HTTPError` or use methods like
        `RequestHandler.redirect` (return None after redirecting to
        halt further processing).  This is where 404 errors for missing files
        are generated.

        .. versionadded:: 3.1
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


plugin = rw.plugin.Plugin(__name__)


@plugin.init
def init(app):
    """serve static files"""
    cfg = app.settings.get('rw.static', {})
    for base_uri, sources in cfg.items():
        full_paths = []
        for source in sources:
            module_name, path = [part.strip() for part in source.split(',')]
            full_path = pkg_resources.resource_filename(module_name, path)
            full_paths.append(full_path)
        app.root.mount('/' + base_uri + '/<path:path>',
                       StaticHandler, {'path': full_paths})
