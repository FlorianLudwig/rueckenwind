# Copyright 2014 Florian Ludwig
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

# PYTHON_ARGCOMPLETE_OK

"""rueckenwind command line tool"""
from __future__ import absolute_import, division, print_function, with_statement

import sys
import os
import argparse
import logging
import logging.config

import yaml
import argcomplete
import pkg_resources
import tornado.httpserver
import tornado.ioloop
import tornado.autoreload
import tornado.util
import jinja2

import rw
import rw.scope
import rw.server
import rw.httpbase


CONFIG_FORMATTER = '%(asctime)s %(name)s[%(levelname)s] %(message)s'
ARG_PARSER = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)
SUB_PARSER = ARG_PARSER.add_subparsers(help='Command help')
LOG = logging.getLogger(__name__)


def command(func):
    """Decorator for CLI exposed functions"""
    func.parser = SUB_PARSER.add_parser(func.__name__, help=func.__doc__)
    func.parser.set_defaults(func=func)
    return func


@command
def serv(args):
    """Serve a rueckenwind application"""
    if not args.no_debug:
        tornado.autoreload.start()

    extra = []

    if sys.stdout.isatty():
        # set terminal title
        sys.stdout.write('\x1b]2;rw: {}\x07'.format(' '.join(sys.argv[2:])))

    if args.cfg:
        extra.append(os.path.abspath(args.cfg))

    listen = (int(args.port), args.address)
    ioloop = tornado.ioloop.IOLoop.instance()
    setup_app(app=args.MODULE, extra_configs=extra,
              ioloop=ioloop, listen=listen)
    ioloop.start()


def setup_app(app, extra_configs=None, ioloop=None, listen=None):
    if ioloop is None:
        ioloop = tornado.ioloop.IOLoop.current()
    if extra_configs is None:
        extra_configs = []

    if isinstance(app, tornado.util.basestring_type):
        module_path = app
        module_name = 'root'
        if ':' in module_path:
            module_path, module_name = module_path.split(':', 1)
        module_path = module_path.replace('/', '.').strip('.')
        module = __import__(module_path, fromlist=[module_name])
        module = getattr(module, module_name)
        app = rw.httpbase.Application(root=module, extra_configs=extra_configs)

    http_server_settings = app.scope['settings'].get('httpserver', {})
    server = tornado.httpserver.HTTPServer(app, **http_server_settings)
    if listen:
        server.listen(*listen)

    scope = rw.scope.Scope()
    with scope():
        ioloop.run_sync(rw.server.start)
    return app.scope


def _add_config_defauts(config):
    config.setdefault('version', 1)
    config.setdefault('disable_existing_loggers', False)
    config.setdefault('formatters', {
        'standard': {
            'format': CONFIG_FORMATTER
        },
    })


def configure_logging_from_env():
    """
LOG_CONFIG Example:

handlers:
  graypy:
    class: graypy.GELFHTTPHandler
    level: INFO
    host: '192.168.91.182'
    port: 12201

loggers:
  '':
    level: DEBUG
    handlers: ['graypy']
    """

    if 'LOG_CONFIG' in os.environ:
        print('using configuration from LOG_CONFIG')
        log_config = yaml.safe_load(os.environ['LOG_CONFIG'])
        _add_config_defauts(log_config)
        print(repr(log_config))
        logging.config.dictConfig(log_config)
    else:
        log_level = os.environ.get('LOG_LEVEL', 'INFO')
        log_level = getattr(logging, log_level)
        logging.basicConfig(level=log_level, format=CONFIG_FORMATTER)


serv.parser.add_argument('-p', '--port', type=str, default='8000',
                         help='Specify port to run http server on')
serv.parser.add_argument('-a', '--address', type=str,
                         help='Specify port to run http server on')
serv.parser.add_argument('--no-debug', action='store_true',
                         help='Run in production mode')
serv.parser.add_argument('-c', '--cfg', type=str,
                         help='Additional config to load')
serv.parser.add_argument('MODULE',
                         help='Module to serve')


def main():
    """Entry point of rw cli"""
    # check logging
    configure_logging_from_env()

    current_path = os.path.abspath('.')
    if current_path not in sys.path:
        sys.path.insert(0, current_path)
    argcomplete.autocomplete(ARG_PARSER)
    args = ARG_PARSER.parse_args()
    args.func(args)
