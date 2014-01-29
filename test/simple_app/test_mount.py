from rw.www import get, mount, RequestHandler, url_for, generate_routing

def test_mount():
    class SubMain(RequestHandler):
        @get('/foo')
        def foo(self):
            self.finish()

        @get('/bar')
        def bar(self):
            self.finish()

    class Main(RequestHandler):
        sub = mount('/sub', SubMain)

        @get('/login')
        def login(self):
            self.finish()

        @get('/logout')
        def logout(self):
            self.finish()

    # generate rounting for Main class
    generate_routing(Main)

    # test url_for
    assert url_for(Main.login) == '/login'
    assert url_for(SubMain.foo) == '/sub/foo'
    assert url_for(Main.sub.foo) == '/sub/foo'