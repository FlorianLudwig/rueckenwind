import pytest

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