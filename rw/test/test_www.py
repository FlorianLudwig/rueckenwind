import rw.www
from rw.www import get

from mock import Mock


def test_basics():
    class Main(rw.www.RequestHandler):
        @get('/login')
        def login(self):
            self.finish()

    assert len(Main.routes) == 1
    assert Main.routes[0].path == '/login'
    assert Main.routes[0].type == 'GET'
    assert Main.routes[0].handler == 'login'  # name of the function


def test_inheritance():
    class Main(rw.www.RequestHandler):
        @get('/login')
        def login(self):
            self.finish()

        @get('/logout')
        def logout(self):
            self.finish()

    class Main2(Main):
        @get('/anmeldung')
        def login(self):
            self.finish()

        @get('/foobar')
        def foobar(self):
            self.finish()

    assert len(Main.routes) == 2
    # the /login route should not exist
    assert len(Main2.routes) == 3

    routes = set([r.path for r in Main2.routes])
    assert routes == set(['/anmeldung', '/foobar', '/logout'])


def test_static_content():
    app = rw.load('rw.test.simple_app')
    content = app.www.Main._static.get_content('static')
    assert content == 'something static\n'


def test_dynamic_static_content():
    app = rw.load('rw.test.simple_app')
    content = app.www.Main._static.get_content('dynamic')
    assert content == 'something dynamic:\n0\n1\n2\n'


def test_templates():
    class Main(rw.www.RequestHandler):
        @get('/')
        def index(self):
            self.finish(template='index.html')

        @get('/impress')
        def impress(self):
            self.template = 'impress.html'
            self.finish()

    app = Mock()
    app.ui_methods = {}
    app.ui_modules = {}
    request = Mock()
    request.headers = {}
    main = Main(app, request)
    #main.index()
    #assert main.template == 'index.html'

    #main.impress()
    #assert main.template == 'impress.html'
