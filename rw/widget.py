
from jinja2 import nodes
from jinja2.ext import Extension


class Widget(Extension):
    # a set of names that trigger the extension.
    tags = set(['widget'])

    def parse(self, parser):
        lineno = parser.stream.next().lineno
        name = parser.parse_condexpr()
        print name.args.insert(0, nodes.Name('handler', 'load'))
        return nodes.CallBlock(self.call_method('_wrapper', [name]), [], [], []).set_lineno(lineno)

    def _wrapper(self, value, caller):
        """(currently) pointless wrapper."""
        return value


class WidgetDef(Extension):
    # a set of names that trigger the extension.
    tags = set(['w'])

    def __init__(self, environment):
        super(Widget, self).__init__(environment)

        # add the defaults to the environment
        environment.extend(
            fragment_cache_prefix='',
            fragment_cache=None
        )

    def parse(self, parser):
        # the first token is the token that started the tag.  In our case
        # we only listen to ``'cache'`` so this will be a name token with
        # `cache` as value.  We get the line number so that we can give
        # that line number to the nodes we create by hand.
        lineno = parser.stream.next().lineno

        # now we parse a single expression that is used as cache key.

        name = parser.stream.next()
        kwargs = nodes.Dict([])
        args = []

        if parser.stream.skip_if('lparen'):
            # parse args
            while 1:
                current = parser.stream.current
                if current.type in ('name', 'integer', 'string', 'float'):
                    args.append(parser.parse_primary())

                next = parser.stream.next()
                if next.type == 'assign':
                    key = nodes.Const(args[-1].name)
                    kwargs.items.append(nodes.Pair(key, parser.parse_primary()))
                    args = args[:-1]
                    next = parser.stream.next()

                if next.type == 'rparen':
                    break
                elif next.type != 'comma':
                    parser.fail(next.type)

        # now we parse the body of the cache block up to `endcache` and
        # drop the needle (which would always be `endcache` in that case)
        # body = parser.parse_statements(['name:endw'], drop_needle=True)

        # now return a `CallBlock` node that calls our _cache_support
        # helper method on this extension.
        return nodes.CallBlock(self.call_method('_cache_support', [nodes.Const(name.value),
                                                                   nodes.List(args),
                                                                   kwargs]),
                               [], [], []).set_lineno(lineno)

    def _cache_support(self, name, args, kwargs, caller):
        """Helper callback."""
        key = self.environment.fragment_cache_prefix + name
        print args, kwargs

        # try to load the block from the cache
        # if there is no fragment in the cache, render it and store
        # it in the cache.
        return None
        rv = self.environment.fragment_cache.get(key)
        if rv is not None:
            return rv
        rv = caller()
        self.environment.fragment_cache.add(key, rv, timeout)
        return rv
