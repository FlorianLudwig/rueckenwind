import rw.www
import mock


class Base(rw.www.RequestHandler):
    @rw.www.get('/foo')
    def foo(self):
        pass


class A(Base):
    pass


class B(Base):
    pass


class Main(rw.www.RequestHandler):
    a = rw.www.mount('/a', A)
    b = rw.www.mount('/b', B)


def test_url_for():
    rw.www.generate_routing(Main)
    assert rw.www.url_for(Main.a.foo) == '/a/foo'
    assert rw.www.url_for(Main.b.foo) == '/b/foo'


