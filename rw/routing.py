import re

from tornado import stack_context


_rule_re = re.compile(r'''
    (?P<static>[^<]*)                           # static rule data
    <
    (?P<variable>[a-zA-Z][a-zA-Z0-9_]*)         # variable name
    (?:
        \:                                      # variable delimiter
        (?P<converter>[a-zA-Z_][a-zA-Z0-9_]*)   # converter name
        (?:\((?P<args>.*?)\))?                  # converter arguments
    )?
    >
''', re.VERBOSE)
_simple_rule_re = re.compile(r'<([^>]+)>')


# from werkzeug.routing
def parse_rule(rule):
    """Parse a rule and return it as generator. Each iteration yields tuples
    in the form ``(converter, arguments, variable)``. If the converter is
    `None` it's a static url part, otherwise it's a dynamic one.

    :internal:
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
        if isinstance(converter, (basestring)):
            converter = {'str': converter_default,
                         'int': converter_int,
                         'uint': converter_uint}[converter]
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


class Rule(object):
    def __init__(self, obj, handler):
        self.path = obj.route
        self.type = obj.route_type
        if hasattr(obj, '__func__'):
            obj.__func__.route_rule = self
        else:
            obj.route_rule = self
        self.handler = handler
        self.route =  list(parse_rule(obj.route))

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

    def match(self, req_handler, request):
        if request.method != self.type and self.type != '*':
            return
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
            with stack_context.ExceptionStackContext(req_handler._stack_context_handle_exception):
                if isinstance(self.handler, basestring):
                    getattr(req_handler, self.handler)(**arguments)
                else:
                    self.handler(req_handler, **arguments)
            return True
        return False

    def get_path(self, values={}):
        re = []
        for converter, args, data in self.route:
            if converter:
                re.append(unicode(values[data]))
            else:
                re.append(data)
        return ''.join(re)

    def __repr__(self):
        return '<Rule %s "%s">' % (self.type, self.path)

