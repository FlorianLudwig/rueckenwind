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
from __future__ import absolute_import, division, print_function, with_statement
import inspect

import re

from future.builtins import range
from tornado import util
import tornado.web

from rw import scope
import rw.plugin


_rule_re = re.compile(r'''
    (?P<static>[^<]*)                           # static rule data
    <
    (?P<variable>[a-zA-Z_][a-zA-Z0-9_]*)         # variable name
    (?:
        \:                                      # variable delimiter
        (?P<converter>[a-zA-Z_][a-zA-Z0-9_]*)   # converter name
        (?:\((?P<args>.*?)\))?                  # converter arguments
    )?
    >
''', re.VERBOSE)
_simple_rule_re = re.compile(r'<([^>]+)>')


class DuplicateError(Exception):
    pass


def parse_rule(rule):
    """Parse a rule and return it as list of tuples in the form
    ``(converter, arguments, variable)``. If the converter is
    `None` it's a static url part, otherwise it's a dynamic one.

    based on werkzeug.routing
    """
    pos = 0
    end = len(rule)
    do_match = _rule_re.match
    used_names = set()
    re = []
    while pos < end:
        m = do_match(rule, pos)
        if m is None:
            break
        data = m.groupdict()
        if data['static']:
            re.append((None, None, data['static']))
        variable = data['variable']
        converter = data['converter'] or 'str'
        # if isinstance(converter, util.basestring_type):
        # TODO create hook for custom converts
        # converter = {'str': converter_default,
        #              'int': converter_int,
        #              'uint': converter_uint,
        # }[converter]
        if variable in used_names:
            raise ValueError('variable name %r used twice.' % variable)
        used_names.add(variable)
        re.append((converter, data['args'] or None, variable))
        pos = m.end()
    if pos < end:
        remaining = rule[pos:]
        if '>' in remaining or '<' in remaining:
            raise ValueError('malformed url rule: %r' % rule)
        re.append((None, None, remaining))
    return re


class NoMatchError(Exception):
    pass


class Route(object):
    def __init__(self, path):
        """Rule for `callback` matching given `path`"""
        self.path = path.rstrip('/')
        self.route = list(parse_rule(path))

    def _sort_struct(self):
        variables = [route[0] for route in self.route if route[0] is not None]
        strings = [route[2] for route in self.route if route[0] is None]
        return variables, strings

    def __lt__(self, o):
        """less than `o`

        :param Route o: other rule to compare with
        """
        if self == o:
            return False

        variables, strings = self._sort_struct()
        variables_o, strings_o = o._sort_struct()
        if len(variables) != len(variables_o):
            return len(variables) < len(variables_o)

        if len(''.join(strings)) != len(''.join(strings_o)):
            return len(''.join(strings)) > len(''.join(strings_o))

        for i in range(len(strings)):
            if strings[i] != strings_o[i]:
                return strings[i] < strings_o[i]

        # strings are the same, so check variables for non-default parser
        for i in range(len(variables)):
            if variables[i] != 'str' and variables_o[i] == 'str':
                return True
        return False

    def __gt__(self, o):
        """greater than `o`

        :param Route o: other rule to compare with
        """
        if self == o:
            return False
        return o < self

    def __eq__(self, o):
        """equal to `o`

        :param Route o: other rule to compare with
        """
        return self.route == o.route

    @rw.scope.inject
    def match(self, test_path, scope):
        arguments = {}
        for converter_name, args, data in self.route:
            if converter_name:
                converters = rw.scope.get('rw.routing:converters')
                converter = converters.get(converter_name)
                if converter is None:
                    raise AttributeError('No converter for {} available'.format(converter_name))
                try:
                    consumed, arguments[data] = converter(test_path)
                except NoMatchError:
                    return None
            elif not test_path.startswith(data):
                return None
            else:
                consumed = len(data)
            test_path = test_path[consumed:]
        if not test_path:
            return arguments
        return None

    def get_path(self, values=None):
        if values is None:
            values = {}
        re = []
        for converter, args, data in self.route:
            if converter:
                re.append(util.unicode_type(values[data]))
            else:
                re.append(data)
        return ''.join(re)

    def __repr__(self):
        return '<Rule "%s">' % self.path


def _generate_request_handler_proxy(handler_class, handler_args, name):
    """When a tornado.web.RequestHandler gets mounted we create a launcher function"""

    @scope.inject
    def request_handler_wrapper(app, handler, **kwargs):
        handler = handler_class(app, handler.request, **handler_args)
        handler._execute([], **kwargs)
    request_handler_wrapper.__name__ = name
    request_handler_wrapper.handler_class = handler_class
    request_handler_wrapper.handler_args = handler_args

    return request_handler_wrapper


class RoutingTable(dict):
    def __init__(self, name):
        dict.__init__(self)
        self.name = name
        self.prefix = ''
        self.sub_rt = []  # child routing tables
        self.fn_namespace = {}
        for method in ['get', 'post', 'put', 'delete', 'options']:
            self[method] = []

    def setup(self):
        """setup routing table"""
        # get all routes from submodules
        for prefix, routes in self.sub_rt:
            routes.prefix = self.prefix + prefix
            routes.setup()

            fn_name_prefixes = {}
            for fn_key, fn in routes.fn_namespace.items():
                self.fn_namespace[routes.name + '.' + fn_key] = fn
                fn_prefix = routes.name
                if '.' in fn_key:
                    fn_prefix += '.' + fn_key.rsplit('.', 1)[0]
                fn_name_prefixes[fn] = fn_prefix

            for key in self:
                funcs = set(rule[1] for rule in self[key])
                for route, route_module, fn in routes.get(key, []):
                    if fn not in funcs:
                        new_route = Route(prefix + route.path)
                        fn.rw_route = new_route
                        fn_name_prefix = fn_name_prefixes[fn]
                        self[key].append((new_route, fn_name_prefix, fn))

        # sort all rules
        for key in self:
            self[key].sort(key=lambda rule: rule[0])

    def add_route(self, method, path, module, fn):
        route = Route(path)
        self.setdefault(method, []).append((route, '', fn))
        # if fn.__name__ in self.fn_namespace:
        #     msg = 'Module already contains route with name {}'.format(fn.__name__)
        #     raise DuplicateError(msg)
        fn.rw_route = route
        self.fn_namespace[fn.__name__] = fn
        return route

    def get_path(self, func, kwargs):
        if func not in self.fn_namespace:
            # TODO do something more sensitve
            # - Log warning
            # - return actual 404 url
            return '404'
        return self.fn_namespace[func].rw_route.get_path(kwargs)

    def add_request_handler(self, path, module, handler_args, name):
        if name is None:
            name = module.__name__
        for method in ['get', 'post', 'put', 'delete']:
            proxy = _generate_request_handler_proxy(module,
                                                    handler_args,
                                                    name + '_' + method)
            if hasattr(module, method):
                route = self.add_route(method, path, module, proxy)
                unbount_method = getattr(module, method)
                if hasattr(unbount_method, '__func__'):
                    # python 2
                    # it is not possible to write to the unbount_method
                    # but writing to the underlying im_func works
                    unbount_method.__func__.rw_route = route
                else:
                    # python 3
                    unbount_method.rw_route = route

    def add_child(self, path, rt):
            # module.routes.prefix = path
        self.sub_rt.append((path, rt))

    def find_route(self, method, path):
        for rule, name_prefix, fn in self[method.lower()]:
            args = rule.match(path)
            if args is not None:
                return name_prefix, fn, args
        return None, None, None


def converter_default(data):
    length = data.find('/')
    if length == 1 or len(data) == 0:
        raise NoMatchError()
    elif length < 0:
        length = len(data)
    return length, util.unicode_type(data[:length])


def converter_path(data):
    """consume rest of the path"""
    return len(data), util.unicode_type(data)


NON_INT = re.compile('[^0-9-]')


def converter_int(data):
    length = NON_INT.search(data)
    length = length.start() if length else len(data)
    if length <= 0:
        raise NoMatchError()
    return length, int(data[:length])


NON_UINT = re.compile('[^0-9]')


def converter_uint(data):
    length = NON_UINT.search(data)
    length = length.start() if length else len(data)
    if length <= 0:
        raise NoMatchError()
    return length, int(data[:length])


plugin = rw.plugin.Plugin(__name__)


@plugin.init
def init(scope):
    scope.setdefault('rw.routing:converters', {}).update({
        'str': converter_default,
        'int': converter_int,
        'uint': converter_uint,
        'path': converter_path
    })
