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

from tornado import util


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
        converter = data['converter'] or converter_default
        if isinstance(converter, util.basestring_type):
            # TODO create hook for custom converts
            converter = {'str': converter_default,
                         'int': converter_int,
                         'uint': converter_uint,
            }[converter]
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


class Rule(object):
    def __init__(self, path, callback):
        """Rule for `callback` matching given `path`"""
        self.path = path
        self.callback = callback
        self.route = list(parse_rule(path))

    def weight(self):
        weight = []
        for converter, args, data in self.route:
            if converter:
                # A variable url part in a routing rule is
                # always to be scored worse than any static
                # rule part, so we assign a score of 4096
                # which is hither than the de facto limit
                # of full urls (~ 2000).
                # http://stackoverflow.com/questions/417142/what-is-the-maximum-length-of-a-url-in-different-browsers
                weight.append(4096)
            else:
                weight.append(len(data))
        return weight

    def _sort_struct(self):
        variables = len([route for route in self.route if route[0] is not None])
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
        if variables != variables_o:
            return variables < variables_o

        if len(''.join(strings)) != len(''.join(strings_o)):
            return len(''.join(strings)) > len(''.join(strings_o))

        for i in xrange(len(strings)):
            if strings[i] != strings_o[i]:
                return strings[i] < strings_o[i]
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

    def match(self, request):
        test_path = request.path
        arguments = {}
        for converter, args, data in self.route:
            if converter:
                try:
                    consumed, arguments[data] = converter(test_path)
                except NoMatchError:
                    return False
            elif not test_path.startswith(data):
                return False
            else:
                consumed = len(data)
            test_path = test_path[consumed:]
        if not test_path:
            return self.callback, arguments
        return False

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
