"""rw event system.


Signal

"""
import traceback

from tornado import gen


class EventException(Exception):
    def __init__(self, exceptions):
        self.exceptions = exceptions
        message = '{} exceptions encountered:\n'.format(len(exceptions))
        for func, e in exceptions:
            message += '{}:\n{}'.format(func, e)
        Exception.__init__(self, ''.join(message))


class Event(set):
    def __init__(self, accumulator=None):
        super(Event, self).__init__()
        self.accumulator = accumulator

    @gen.coroutine
    def __call__(self, *args, **kwargs):
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
            except Exception as e:
                exceptions.append((func, traceback.format_exc()))

        # wait for results
        for func, future in futures:
            try:
                result = yield future
                re.append(result)
            except Exception as e:
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