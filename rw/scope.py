# Copyright 2014 Florian Ludwig
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from __future__ import absolute_import, division, print_function, with_statement

import sys
import contextlib
import functools
import inspect

from tornado import stack_context

import rw.gen


NOT_PROVIDED = object()
SCOPE_CHAIN = None


class OutsideScopeError(Exception):
    pass


class Scope(dict):
    def __init__(self, name=None):
        super(Scope, self).__init__()
        self._provider = {}
        self._subscopes = {}
        self.name = name
        self.plugins = set()

    def provider(self, key, provider):
        self._provider[key] = provider

    @rw.gen.coroutine
    def activate(self, plugin):
        yield plugin.activate()
        self.plugins.add(plugin)

    def subscope(self, key):
        if key not in self._subscopes:
            name = '{}.{}'.format(self.name, key)
            subscope = SubScope(name, self)
            self._subscopes[key] = subscope
        return self._subscopes[key]

    def get(self, key, default=NOT_PROVIDED, scopes=None):
        """

        :param str key:
        :param default:
        :param list[Scope] scopes:
        :param str prefix:
        :return: :raise IndexError:
        """
        if scopes is None:
            scopes = list(reversed(SCOPE_CHAIN))
        if key == 'scope':
            return self

        for i, scope in enumerate(scopes):
            if key in scope:
                return scope[key]
            elif key in scope._provider:
                scope[key] = scope._provider[key]()
                del scope._provider[key]
                return scope[key]
            elif key in scope._subscopes:
                return SubScopeView(key, scopes)

        if default is not NOT_PROVIDED:
            return default

        msg = 'No value for "{}" stored and no default given'.format(key)
        raise IndexError(msg)

    def __call__(self):
        return stack_context.StackContext(functools.partial(set_context, self))


class SubScope(Scope):
    def __init__(self, name, parent):
        self.parent = parent
        super(SubScope, self).__init__(name)


class SubScopeView(object):
    def __init__(self, key, scope_chain):
        self.key = key
        self.scope_chain = scope_chain

    def __getitem__(self, item):
        for scope in self.scope_chain:
            if self.key in scope._subscopes:
                if item in scope._subscopes[self.key]:
                    return scope._subscopes[self.key][item]
        raise IndexError()

    def __eq__(self, other):
        return (
            isinstance(other, SubScopeView)
            and self.key == other.key
            and self.scope_chain == other.scope_chain
        )


@contextlib.contextmanager
def set_context(scope):
    global SCOPE_CHAIN
    if SCOPE_CHAIN is None:
        SCOPE_CHAIN = []
    SCOPE_CHAIN.append(scope)
    try:
        yield
    finally:
        # TODO write unit test to get current_scope to be None
        SCOPE_CHAIN.pop()


def get_current_scope():
    return SCOPE_CHAIN[-1] if SCOPE_CHAIN else None


def get(key, default=NOT_PROVIDED):
    if not SCOPE_CHAIN:
        raise OutsideScopeError()
    return SCOPE_CHAIN[-1].get(key, default, list(reversed(SCOPE_CHAIN)))


def inject(fn):
    fn_inspect = getattr(fn, '_rw_wrapped_function', fn)
    arg_spec = inspect.getargspec(fn_inspect)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if len(args) < len(arg_spec.args):
            # possible injection
            missing_args = set(arg_spec.args[len(args):])
            for key in missing_args:
                if key not in kwargs:
                    if not SCOPE_CHAIN:
                        raise OutsideScopeError('Cannot use inject outside of scope')
                    try:
                        kwargs[key] = get(key)
                    except IndexError:
                        # the key might not be inside scope but there might be
                        # a default parameter defined inside the function
                        pass

        try:
            return fn(*args, **kwargs)
        except:
            msg = 'Error injecting into {}.{}'
            print(msg.format(fn.__module__, fn.__name__), file=sys.stderr)
            raise

    return wrapper


@rw.gen.coroutine
def setup_app_scope(name, scope, settings):
    """Load confing and activate plugins accordingly"""
    scope['settings'] = settings

    # load plugins
    plugins = []
    for plugin_name, active in settings.get('rw.plugins', {}).items():
        plugin = __import__(plugin_name)
        plugin_path = plugin_name.split('.')[1:] + ['plugin']
        for sub in plugin_path:
            plugin = getattr(plugin, sub)
        plugins.append(scope.activate(plugin))

    yield plugins
    raise rw.gen.Return(settings)
