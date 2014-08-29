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

from tornado import stack_context, gen
import contextlib
import functools

import inspect

NOT_PROVIDED = object()
SCOPE_CHAIN = None


class OutsideScopeError(Exception):
    pass


class Scope(dict):
    def __init__(self, name=None):
        super(Scope, self).__init__()
        self._provider = {}
        self.name = name
        self.plugins = set()

    def provider(self, key, provider):
        self._provider[key] = provider

    @gen.coroutine
    def activate(self, plugin):
        yield plugin.activate()
        self.plugins.add(plugin)

    def __call__(self):
        return stack_context.StackContext(functools.partial(set_context, self))


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
    if key == 'scope':
        return SCOPE_CHAIN[-1]

    for scope in reversed(SCOPE_CHAIN):
        if key in scope:
            return scope[key]
        elif key in scope._provider:
            scope[key] = scope._provider[key]()
            del scope._provider[key]
            return scope[key]

    if default is not NOT_PROVIDED:
        return default

    msg = 'No value for "{}" stored and no default given'.format(key)
    raise IndexError(msg)


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
                    kwargs[key] = get(key)
        return fn(*args, **kwargs)
    return wrapper