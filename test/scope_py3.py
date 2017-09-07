import rw.scope


def test_python3_typehinted_injection():
    scope = rw.scope.Scope()
    scope['some_static_value'] = 42

    @rw.scope.inject
    def bar(some_static_value: int):
        return some_static_value

    with scope():
        assert bar() == 42
