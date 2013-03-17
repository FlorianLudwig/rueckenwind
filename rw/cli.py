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

"""rueckenwind command line tool"""
import sys
import os
import argparse
import logging

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


def generate(src, dst, data):
    for fname in pkg_resources.resource_listdir(__name__, src):
        path = src + '/' + fname
        if pkg_resources.resource_isdir(__name__, path):
            os.mkdir(dst + '/' + fname)
            generate(path, dst + '/' + fname, data)
        else:
            tpl = pkg_resources.resource_string(__name__, path)
            tpl = tpl.decode('utf-8')
            content = jinja2.Template(tpl).render(**data)
            open(dst + '/' + fname, 'w').write(content.encode('utf-8'))


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
    generate('skel', os.path.abspath(name), {'name': name})

skel.parser.add_argument('--name', type=str,
                         help='Name of the module to be created')


@command
def serv(args):
    """Serve a rueckenwind application"""
    import rw
    rw.DEBUG = not args.no_debug
    module = args.MODULE.replace('/', '.').strip('.')
    rw.start(module, address=args.address, port=args.port)

serv.parser.add_argument('-p', '--port', type=int, default=8000,
                         help='Specifiy port to run http server on')
serv.parser.add_argument('-a', '--address', type=str,
                         help='Specifiy port to run http server on')
serv.parser.add_argument('--no-debug', action='store_true',
                         help='Run in production mode')
serv.parser.add_argument('MODULE',
                         help='Module to serv')


def main():
    # check logging
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    logging.basicConfig(level=getattr(logging, log_level),
                        format='%(asctime)s %(name)s[%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    current_path = os.path.abspath('.')
    if not current_path in sys.path:
        sys.path.insert(0, current_path)
    args = ARG_PARSER.parse_args()
    args.func(args)
