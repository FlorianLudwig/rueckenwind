from __future__ import absolute_import, division, print_function, with_statement

import pytest
from tornado import concurrent

import tornado.gen
import tornado.testing

import rw.scope


def test_low_level_api():
    scope = rw.scope.Scope()
    current_user = object()

    def get_current_user():
        get_current_user.runs += 1
        return current_user
    scope.provider('user', get_current_user)
    get_current_user.runs = 0

    assert get_current_user.runs == 0
    assert scope.get('user') is current_user
    assert get_current_user.runs == 1
    # make sure provider is not run twice
    scope.get('user')
    assert get_current_user.runs == 1

    assert scope.get('unknown value', 'default') == 'default'
    with pytest.raises(IndexError):
        scope.get('unknown value')


def test_basic():
    scope = rw.scope.Scope()
    scope['some_static_value'] = 42
    current_user = object()

    def get_current_user():
        return current_user
    scope.provider('user', get_current_user)

    @rw.scope.inject
    def foo(user):
        return user

    @rw.scope.inject
    def bar(some_static_value):
        return some_static_value

    with scope():
        assert foo() is current_user
        assert foo(1) == 1
        assert foo() is current_user
        assert bar() == 42

        # check nested scope
        nested_scope = rw.scope.Scope()
        nested_scope['user'] = 2
        with nested_scope():
            assert foo() == 2
            assert bar() == 42

        assert foo() is current_user
        assert bar() == 42


def test_fail():
    @rw.scope.inject
    def foo(something_to_inject):
        pass

    with pytest.raises(rw.scope.OutsideScopeError):
        foo()

    # if all arguments are provided we are ok to run outside of a scope
    foo(something_to_inject=1)


class ConcurrencyTest(tornado.testing.AsyncTestCase):
    """test concurrent ioloop futures inside different scopes

    Three tests with different resultion order
    """
    @tornado.testing.gen_test
    def test_concurrent_scopes_both(self):
        """set both results before yield-ing"""
        future_a, future_b = self.setup()

        self.lock_a.set_result(None)
        self.lock_b.set_result(None)

        assert (yield future_b) == 'b'
        assert (yield future_a) == 'a'

    @tornado.testing.gen_test
    def test_concurrent_scopes_ba(self):
        """b then a"""
        future_a, future_b = self.setup()

        self.lock_b.set_result(None)
        assert (yield future_b) == 'b'

        self.lock_a.set_result(None)
        assert (yield future_a) == 'a'

    @tornado.testing.gen_test
    def test_concurrent_scopes_ab(self):
        """a then b"""
        future_a, future_b = self.setup()

        self.lock_a.set_result(None)
        assert (yield future_a) == 'a'

        self.lock_b.set_result(None)
        assert (yield future_b) == 'b'

    def setup(self):
        """Setup two scopes and two "locks"."""
        self.scope_a = rw.scope.Scope()
        self.scope_a['name'] = 'a'
        self.lock_a = concurrent.Future()
        self.scope_b = rw.scope.Scope()
        self.scope_b['name'] = 'b'
        self.lock_b = concurrent.Future()

        @rw.scope.inject
        def get_name(name):
            return name

        @tornado.gen.coroutine
        def thread_a():
            yield self.lock_a
            raise tornado.gen.Return(get_name())

        @tornado.gen.coroutine
        def thread_b():
            yield self.lock_b
            raise tornado.gen.Return(get_name())

        with self.scope_a():
            future_a = thread_a()

        with self.scope_b():
            future_b = thread_b()

        return future_a, future_b