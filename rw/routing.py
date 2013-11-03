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

import re

from bson import ObjectId
from bson.objectid import InvalidId


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
        if isinstance(converter, basestring):
            converter = {'str': converter_default,
                         'int': converter_int,
                         'uint': converter_uint,
                         'ObjectId': converter_object_id}[converter]
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
    return length, unicode(data[:length])


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


def converter_object_id(data):
    try:
        _id = ObjectId(data[:24])
    except InvalidId, e:
        raise NoMatchError()
    return 24, _id


class Rule(object):
    def __init__(self, path, handler, func_name):
        self.path = path
        self.handler = handler
        self.func_name = func_name
        self.route = list(parse_rule(path))

    def weight(self):
        c = 0
        for converter, args, data in self.route:
            if converter:
                c += 1
            else:
                c += len(data)
        return c

    def __cmp__(self, o):
        return cmp(self.weight(), o.weight())

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
            return self.handler, self.func_name, arguments
        return False

    def get_path(self, values=None):
        if values is None:
            values = {}
        re = []
        for converter, args, data in self.route:
            if converter:
                re.append(unicode(values[data]))
            else:
                re.append(data)
        return ''.join(re)

    def __repr__(self):
        return '<Rule "%s">' % self.path
