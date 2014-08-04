from __future__ import absolute_import, division, print_function, with_statement

import pytest
import rw.event

import tornado.gen
import tornado.testing


@tornado.gen.coroutine
def something_lazy(x):
    for i in range(x):
        yield something_lazy(0)
    raise tornado.gen.Return(x)


class MyTestCase(tornado.testing.AsyncTestCase):
    @tornado.testing.gen_test
    def test_exception_handling(self):
        MY_EVENT = rw.event.Event('MY_EVENT')

        @MY_EVENT.add
        def fail():
            1 / 0

        with pytest.raises(rw.event.EventException):
            yield MY_EVENT()

        try:
            yield MY_EVENT()
            assert False  # this line should never be reached
        except rw.event.EventException as e:
            # the original traceback should be get printed
            assert 'in fail' in str(e)  # function name of the actual exception
            assert '1 / 0' in str(e)  # the source line of the exception
            assert 'ZeroDivisionError' in str(e)

    @tornado.testing.gen_test
    def test_event_listener(self):
        MY_EVENT = rw.event.Event('MY_EVENT')
        args = []

        def listener(greeting):
            args.append(greeting)

        MY_EVENT.add(listener)

        yield MY_EVENT('Hello World')
        assert args == ['Hello World']
        MY_EVENT.remove(listener)
        assert len(MY_EVENT) == 0

    @tornado.testing.gen_test
    def test_decorator(self):
        MY_EVENT = rw.event.Event('MY_EVENT')
        args = []

        @MY_EVENT.add
        def listener(greeting):
            args.append(greeting)

        yield MY_EVENT('Hallo Welt')
        assert args == ['Hallo Welt']

    @tornado.testing.gen_test
    def test_accumulator(self):
        MY_EVENT = rw.event.Event('MY_EVENT', sum)
        MY_EVENT.add(lambda: 1)
        MY_EVENT.add(lambda: 2)

        assert (yield MY_EVENT()) == 3

    @tornado.testing.gen_test
    def test_futures(self):
        MY_EVENT = rw.event.Event('MY_EVENT')
        MY_EVENT.add(something_lazy)
        result = yield MY_EVENT(12)
        assert result == [12]

    @tornado.testing.gen_test
    def test_futures_fail(self):
        @tornado.gen.coroutine
        def something_lazy_failing():
            yield something_lazy(1)
            1 / 0

        MY_EVENT = rw.event.Event('MY_EVENT')
        MY_EVENT.add(something_lazy_failing)

        with pytest.raises(rw.event.EventException):
            yield MY_EVENT()

        try:
            yield MY_EVENT()
            assert False  # this line should never be reached
        except rw.event.EventException as e:
            # the original traceback should be get printed
            assert 'in something_lazy_failing' in str(e)  # function name of the actual exception
            assert '1 / 0' in str(e)  # the source line of the exception
            assert 'ZeroDivisionError' in str(e)