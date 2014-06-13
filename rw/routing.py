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

import re

from future.builtins import range
from tornado import util

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


class Rule(object):
    def __init__(self, path):
        """Rule for `callback` matching given `path`"""
        self.path = path
        self.route = list(parse_rule(path))

    def _sort_struct(self):
        variables = [route[0] for route in self.route if route[0] is not None]
        strings = [route[2] for route in self.route if route[0] is None]
        return variables, strings

    def __lt__(self, o):
        """less than `o`

        :param Rule o: other rule to compare with
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

        :param Rule o: other rule to compare with
        """
        if self == o:
            return False
        return o < self

    def __eq__(self, o):
        """equal to `o`

        :param Rule o: other rule to compare with
        """
        return self.route == o.route

    @rw.scope.inject
    def match(self, test_path, scope):
        arguments = {}
        for converter_name, args, data in self.route:
            if converter_name:
                converters = scope.get('rw.routing:converters')
                converter = converters.get(converter_name)
                if converter is None:
                    raise AttributeError('No converter for {} avaiable'.format(converter_name))
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


class RoutingTable(dict):
    def setup(self):
        """setup routing table"""

        # sort all rules
        for key in self:
            self[key].sort()

    def add_route(self, method, path, fn):
        self.setdefault(method, []).append((Rule(path), fn))

    def find_route(self, method, path):
        for rule, fn in self.get(method.lower(), []):
            args = rule.match(path)
            if args is not None:
                return fn, args
        return None, None


def converter_default(data):
    length = data.find('/')
    if length == 1 or len(data) == 0:
        raise NoMatchError()
    elif length < 0:
        length = len(data)
    return length, util.unicode_type(data[:length])


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
    })

