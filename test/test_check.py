import pytest
from rw.www import RequestHandler, RequestSubHandler
from rw.check import Protector, overwrite, overwrite_protected, OverwriteException


def test_decorator():
    class Base(Protector):
        @overwrite_protected
        def finish(self):
            return 'finish'

    # operators should not change the functions
    assert Base().finish() == 'finish'

    @overwrite
    def bar():
        return 'bar'
    assert bar() == 'bar'


def test_overwrite():
    print '-------------'
    class Base(Protector):
        @overwrite_protected
        def finish(self):
            return 'finish'

        @overwrite_protected
        def finish2(self):
            return 'finish'
    print '-------------'

    # overwrite
    with pytest.raises(OverwriteException):
        class Foo(Base):
            def finish(self):
                pass

    with pytest.raises(OverwriteException):
        class Foo(Base):
            def finish2(self):
                pass

    # overwrite with explicit decorator should throw no exception
    class Foo(Base):
        @overwrite
        def finish(self):
            return super(Foo, self).finish()

    assert Foo().finish() == 'finish'


def test_overwrite_protection_for_base_class():
    class Base(dict, Protector):
        overwrite_protected(dict.update)

    # overwrite
    with pytest.raises(OverwriteException):
        class Foo(Base):
            def update(self):
                pass

    # overwrite with explicit decorator should throw no exception
    class Foo(Base):
        @overwrite
        def update(self, other):
            return super(Foo, self).update(other)

    f = Foo()
    assert 'a' not in f
    f.update({'a': 1})
    assert 'a' in f


def test_protection_of_request_handler():
    with pytest.raises(OverwriteException):
        class TestHandler(RequestHandler):
            def update(self):
                self.finish('oops')


    with pytest.raises(OverwriteException):
        class Foo(RequestHandler):
            pass

        class Bar(Foo):
            def update(self):
                self.finish('oops')

    with pytest.raises(OverwriteException):
        class Bar(RequestSubHandler):
            def update(self):
                self.finish('oops')