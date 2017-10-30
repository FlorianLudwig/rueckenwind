"""An example using as many different features of rueckenwind as possible

"""
import time

import tornado.web
import tornado.ioloop
import rw.testing
import rw.http
import rw.httpbase
from rw import gen

# every rueckenwind projects needs at least one rw.http.Module
root = rw.http.Module('test.example')


@root.init
def init(template_env):
    # init is executed during startup
    #
    # Here we add a global variable to the template environment
    # every module has a seperate jinja2 template environment
    template_env.globals['static_value'] = 42
    # assert template_env is root.template_env


@root.get('/')
def index(handler):
    handler.finish('Hello World')


@root.get('/hello_handler')
def hello_return(handler):
    # the http decorators (get etc.) of rw.http.Module provide
    # dependency inection via rw.scope.
    # This way the current handler (rw.httpbase.RequestHandler) is injected
    # and can be used to responed to the current http request via
    # handler.finish()
    handler.finish('Hello Handler!')


@root.get('/lazy')
@gen.coroutine
def lazy(handler):
    # function can be gen.coroutines so async operations can be yielded
    yield gen.Task(tornado.ioloop.IOLoop.current().add_timeout, time.time())
    handler.finish('Hello lazy rw.http')


@root.post('/')
def root_submit(handler):
    handler.finish('root POST')


# TODO support: @root.get('/user', defaults={'name': 'me'})
@root.get('/user/<name>')
def user_page(handler, name):
    handler.finish('Hello ' + name)


@root.get('/otherplace')
def other(handler):
    handler.finish('other')


@root.put('/put')
def put(handler):
    handler.finish('put')


@root.delete('/delete')
def delete(handler):
    handler.finish('delete')


@root.options('/options')
def options(handler):
    handler.finish('options')


@root.get('/foo')
def some_page():
    return root.render_template('index.html')


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Tornado GET")

    def post(self):
        self.write("Tornado POST")


sub = rw.http.Module(name='submodule', resources='test.example')


@sub.init
def sub_init(template_env):
    template_env.globals['static_value'] = 42
    # assert template_env is root.template_env


@sub.get('/')
def sub_index():
    return sub.render_template('sub.html')


root.mount('/tornado', MainHandler)
root.mount('/sub', sub)
