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

from tornado import gen


class Event(set):
    """
    A simple within-process pub/sub event system.

    If multiple callbacks are provided and raise exceptions,
    the first detected exception is re-raised and all successive exceptions are ignored.
    """

    def __init__(self, name, accumulator=None):
        super(Event, self).__init__()
        self.name = name
        self.accumulator = accumulator

    @gen.coroutine
    def __call__(self, *args, **kwargs):
        re = []
        futures = []
        for func in self:
            result = func(*args, **kwargs)
            if isinstance(result, gen.Future):
                # we are not waiting for future objects result here
                # so they evaluate in parallel
                futures.append((func, result))
            else:
                re.append(result)

        # wait for results
        for func, future in futures:
            if not future.done():
                yield future
            re.append(future.result())

        # apply accumulator
        if self.accumulator:
            re = self.accumulator(re)

        raise gen.Return(re)

    def add(self, func):
        assert callable(func)
        set.add(self, func)
        return func
