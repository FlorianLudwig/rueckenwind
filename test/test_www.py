import rw.www
from rw.www import get, generate_routing

from mock import Mock


def test_basics():
    class Main(rw.www.RequestHandler):
        @get('/login')
        def login(self):
            self.finish()

    routes = rw.www.generate_routing(Main)['get']
    assert len(routes) == 1
    assert routes[0].path == '/login'
    assert routes[0].func_name == 'login'  # name of the function


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

    routes = rw.www.generate_routing(Main)['get']
    routes2 = rw.www.generate_routing(Main2)['get']
    assert len(routes) == 2
    # the /login route should not exist twice
    assert len(routes2) == 3

    routes = set([r.path for r in routes2])
    assert routes == set(['/anmeldung', '/foobar', '/logout'])


def test_static_content():
    app = rw.get_module('test.simple_app')
    print app
    print dir(app)
    content = app.www.Main._static.get_content('static.html')
    assert content == 'something static\n'


def test_dynamic_static_content():
    app = rw.get_module('test.simple_app')
    content = app.www.Main._static.get_content('dynamic.html')
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

    generate_routing(Main)
    main = Main(app, request)
    #main.index()
    #assert main.template == 'index.html'

    #main.impress()
    #assert main.template == 'impress.html'
