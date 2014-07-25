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

# PYTHON_ARGCOMPLETE_OK

"""rueckenwind command line tool"""
import shutil
import sys
import os
import argparse
import logging

import argcomplete
import pkg_resources
import jinja2


ARG_PARSER = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)
SUB_PARSER = ARG_PARSER.add_subparsers(help='Command help')


def command(func):
    """Decorator for CLI exposed functions"""
    func.parser = SUB_PARSER.add_parser(func.func_name, help=func.__doc__)
    func.parser.set_defaults(func=func)
    return func


def create_skel(src, dst, data):
    """generate skeleton rw project"""
    for fname in pkg_resources.resource_listdir(__name__, src):
        path = src + '/' + fname
        if pkg_resources.resource_isdir(__name__, path):
            os.mkdir(dst + '/' + fname)
            create_skel(path, dst + '/' + fname, data)
        elif fname.endswith('.py') or fname.endswith('.html'):
            tpl = pkg_resources.resource_string(__name__, path)
            tpl = tpl.decode('utf-8')
            content = jinja2.Template(tpl).render(**data)
            open(dst + '/' + fname, 'w').write(content.encode('utf-8'))
        elif fname.endswith('.css') or fname.endswith('.png'):
            src = pkg_resources.resource_filename(__name__, path)
            shutil.copy(src, dst + '/' + fname)


@command
def skel(args):
    """Generate a skeleton project"""
    if args.name:
        name = args.name
    else:
        name = raw_input('Name: ')
    if os.path.exists(name):
        print 'Already exists'
        sys.exit(1)

    os.mkdir(name)
    create_skel('skel', os.path.abspath(name), {'name': name})

skel.parser.add_argument('--name', type=str,
                         help='Name of the module to be created')


@command
def serv(args):
    """Serve a rueckenwind application"""
    import rw
    rw.DEBUG = not args.no_debug
    module = args.MODULE.replace('/', '.').strip('.')
    extra = []

    if sys.stdout.isatty():
        sys.stdout.write('\x1b]2;rw: {}\x07'.format(' '.join(sys.argv[2:])))

    if args.cfg:
        extra.append(os.path.abspath(args.cfg))
    rw.start(module, extra_config_files=extra, address=args.address, port=args.port)

serv.parser.add_argument('-p', '--port', type=str, default='8000+',
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
    if not current_path in sys.path:
        sys.path.insert(0, current_path)
    argcomplete.autocomplete(ARG_PARSER)
    args = ARG_PARSER.parse_args()
    args.func(args)
