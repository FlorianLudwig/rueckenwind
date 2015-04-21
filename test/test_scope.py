from __future__ import absolute_import, division, print_function, with_statement

import pytest
from tornado import concurrent

import tornado.gen
import tornado.testing

import rw.scope


# def test_low_level_api():
#     scope = rw.scope.Scope()
#     current_user = object()
#
#     def get_current_user():
#         get_current_user.runs += 1
#         return current_user
#     scope.provider('user', get_current_user)
#     get_current_user.runs = 0
#
#     assert get_current_user.runs == 0
#     assert rw.scope.get('user') is current_user
#     assert get_current_user.runs == 1
#     # make sure provider is not run twice
#     rw.scope.get('user')
#     assert get_current_user.runs == 1
#
#     assert scope.get('unknown value', 'default') == 'default'
#     with pytest.raises(IndexError):
#         scope.get('unknown value')


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

    @rw.scope.inject
    def some_function_with_a_default_value(my_paramenter='my_default_value'):
        return my_paramenter

    with scope():
        assert foo() is current_user
        assert foo(1) == 1
        assert foo() is current_user
        assert bar() == 42
        assert bar(10) == 10
        assert bar(some_static_value=11) == 11

        # normal calling behaviour must be preserved
        assert some_function_with_a_default_value('value') == 'value'
        assert some_function_with_a_default_value() == 'my_default_value'

        # check nested scope
        nested_scope = rw.scope.Scope()
        nested_scope['user'] = 2
        with nested_scope():
            assert foo() == 2
            assert bar() == 42

        assert foo() is current_user
        assert bar() == 42


def test_recursion():
    """Entering the same scope twice should not produce unexpected behaviour"""
    scope = rw.scope.Scope()
    scope2 = rw.scope.Scope()

    with scope():
        assert rw.scope.get_current_scope() is scope
        with scope2():
            assert rw.scope.get_current_scope() is scope2
            with scope2():
                assert rw.scope.get_current_scope() is scope2
                with scope():
                    assert rw.scope.get_current_scope() is scope
                assert rw.scope.get_current_scope() is scope2
            assert rw.scope.get_current_scope() is scope2
        assert rw.scope.get_current_scope() is scope

    assert rw.scope.get_current_scope() is None


def test_sub_scope():
    scope1 = rw.scope.Scope()
    scope2 = rw.scope.Scope()
    scope3 = rw.scope.Scope()

    sub1 = scope1.subscope('my_sub_scope')
    sub2 = scope2.subscope('my_sub_scope')

    sub1['value_1'] = 1
    sub1['shared'] = 1
    sub2['value_2'] = 2
    sub2['shared'] = 2

    @rw.scope.inject
    def get_sub_scope(my_sub_scope):
        return my_sub_scope

    @rw.scope.inject
    def get_sub_scope_var(var, my_sub_scope):
        return my_sub_scope[var]

    def checks_inside_scope1():
        assert rw.scope.get('my_sub_scope') == get_sub_scope()
        assert rw.scope.get('my_sub_scope')['value_1'] == 1
        assert get_sub_scope_var('value_1') == 1
        assert rw.scope.get('my_sub_scope')['shared'] == 1
        assert get_sub_scope_var('shared') == 1
        assert 'value_2' not in rw.scope.get('my_sub_scope')

    def checks_inside_scope2():
        assert rw.scope.get('my_sub_scope') == get_sub_scope()
        assert rw.scope.get('my_sub_scope')['value_1'] == 1
        assert get_sub_scope_var('value_1') == 1
        assert rw.scope.get('my_sub_scope')['value_2'] == 2
        assert get_sub_scope_var('value_2') == 2
        assert rw.scope.get('my_sub_scope')['shared'] == 2
        assert get_sub_scope_var('shared') == 2

    with scope1():
        checks_inside_scope1()
        with scope2():
            checks_inside_scope2()
            with scope3():
                # scope 3 does not have a 'my_sub_scope' subscope
                # so we expect the same results as for scope 2
                checks_inside_scope2()

        checks_inside_scope1()


def test_fail():
    @rw.scope.inject
    def foo(something_to_inject):
        pass

    with pytest.raises(rw.scope.OutsideScopeError):
        foo()

    # if all arguments are provided we are ok to run outside of a scope
    foo(something_to_inject=1)


class ScopeLeakingTest(tornado.testing.AsyncTestCase):
    def test_scope_leaking(self):
        # if an exception ocurus inside a scope the scope might not
        # get clean up correctly.
        scope = rw.scope.Scope()

        with pytest.raises(NotImplementedError):
            with scope():
                raise NotImplementedError('Just some random error')

        # no we are outside of the scope
        assert rw.scope.get_current_scope() is None


class ConcurrencyTest(tornado.testing.AsyncTestCase):
    """test concurrent ioloop futures inside different scopes

    Three tests with different resolution order
    """
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
