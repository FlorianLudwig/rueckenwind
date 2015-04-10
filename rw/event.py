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

"""rw event system.


Signal

"""
from __future__ import absolute_import, division, print_function, with_statement

import traceback

from tornado import gen
import rw.scope


class EventException(Exception):
    def __init__(self, exceptions):
        self.exceptions = exceptions
        message = '{} exceptions encountered:\n'.format(len(exceptions))
        for func, e in exceptions:
            message += '{}:\n{}'.format(func, e)
        Exception.__init__(self, ''.join(message))


class Event(set):
    def __init__(self, name, accumulator=None):
        super(Event, self).__init__()
        self.name = name
        self.accumulator = accumulator

    @gen.coroutine
    def __call__(self, *args, **kwargs):
        scope = rw.scope.get_current_scope()
        rw_tracing = scope.get('rw_trace', None) if scope else None

        re = []
        exceptions = []
        futures = []
        for func in self:
            try:
                result = func(*args, **kwargs)
                if isinstance(result, gen.Future):
                    # we are not waiting for future objects result here
                    # so they evaluate in parallel
                    futures.append((func, result))
                else:
                    re.append(result)
            except Exception:
                exceptions.append((func, traceback.format_exc()))

        # wait for results
        for func, future in futures:
            try:
                if not future.done():
                    yield future
                re.append(future.result())

            except Exception:
                exceptions.append((func, traceback.format_exc()))

        if exceptions:
            raise EventException(exceptions)

        # apply accumolator
        if self.accumulator:
            re = self.accumulator(re)

        raise gen.Return(re)

    def add(self, func):
        assert callable(func)
        set.add(self, func)
        return func
