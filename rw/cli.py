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

import shutil
import sys
import os
import argparse
import logging

import argcomplete
import pkg_resources
import tornado.httpserver
import tornado.ioloop
import tornado.autoreload
import tornado.util
import jinja2

import rw
import rw.scope
import rw.cfg
import rw.server
import rw.httpbase


ARG_PARSER = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)
SUB_PARSER = ARG_PARSER.add_subparsers(help='Command help')


def command(func):
    """Decorator for CLI exposed functions"""
    func.parser = SUB_PARSER.add_parser(func.__name__, help=func.__doc__)
    func.parser.set_defaults(func=func)
    return func


def create_skel(src, dst, data):
    """generate skeleton rw project"""
    dst = dst.format(**data)
    if not os.path.exists(dst):
        os.makedirs(dst)

    for fname in pkg_resources.resource_listdir(__name__, src):
        path = os.path.join(src, fname)
        dest_fname = os.path.join(dst, fname.format(**data))
        ext = os.path.splitext(fname)[1].lower()

        if pkg_resources.resource_isdir(__name__, path):
            create_skel(path, dst + '/' + fname, data)
        elif ext in ('.py', '.svg', '.yml'):
            tpl = pkg_resources.resource_string(__name__, path)
            tpl = tpl.decode('utf-8')
            content = jinja2.Template(tpl).render(**data)
            open(dest_fname, 'w').write(content.encode('utf-8'))
        elif ext in ('.css', '.png', '.html'):
            src = pkg_resources.resource_filename(__name__, path)
            shutil.copy(src, dest_fname)


@command
def skel(args):
    """Generate a skeleton project"""
    if args.name:
        name = args.name
    else:
        name = raw_input('Name: ')
    if os.path.exists(name):
        print('Already exists')
        sys.exit(1)

    os.mkdir(name)
    create_skel('skel', os.path.abspath(name), {'name': name})

skel.parser.add_argument('--name', type=str,
                         help='Name of the module to be created')


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
    setup_app(app=args.MODULE, extra_configs=extra, ioloop=ioloop, listen=listen)
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
        settings = rw.cfg.read_configs(module.name, extra_configs)
        app = rw.httpbase.Application(root=module, rw_settings=settings)
    elif hasattr(app, 'rw_settings'):
        settings = app.rw_settings
    else:
        settings = {}

    server = tornado.httpserver.HTTPServer(app, **settings.get('httpserver', {}))
    if listen:
        server.listen(*listen)

    scope = rw.scope.Scope()
    with scope():
        ioloop.run_sync(rw.server.start)
    return app.scope


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
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    logging.basicConfig(level=getattr(logging, log_level),
                        format='%(asctime)s %(name)s[%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    current_path = os.path.abspath('.')
    if current_path not in sys.path:
        sys.path.insert(0, current_path)
    argcomplete.autocomplete(ARG_PARSER)
    args = ARG_PARSER.parse_args()
    args.func(args)
