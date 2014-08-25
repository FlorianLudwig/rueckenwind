from __future__ import absolute_import, division, print_function, with_statement

import pkg_resources
import tornado.web

import rw.plugin


class StaticHandler(tornado.web.StaticFileHandler):
    pass


plugin = rw.plugin.Plugin(__name__)


@plugin.init
def init(app):
    """serve static files"""
    cfg = app.settings.get('rw.static', {})
    for base_uri, sources in cfg.items():
        path = sources[0]
        module_name, path = [part.strip() for part in path.split(',')]
        full_path = pkg_resources.resource_filename(module_name, path)
        app.root.mount('/' + base_uri + '/<path:path>',
                       StaticHandler, {'path': full_path})
