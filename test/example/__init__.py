"""An example using as many different features of rueckenwind as possible

"""
import os
import time

import tornado.web
import tornado.ioloop
import rw.testing
import rw.http
import rw.httpbase
from rw import gen


BASE_PATH = os.path.abspath(os.path.dirname(__file__))


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Tornado GET")

    def post(self):
        self.write("Tornado POST")


sub = rw.http.Module(name='submodule', resources='test.example')


@sub.get('/')
def sub_index():
    sub.render_template('sub.html')


root = rw.http.Module('test.example')
root.mount('/tornado', MainHandler)
root.mount('/sub', sub)


@root.init
def init(template_env):
    template_env.globals['static_value'] = 42


@root.get('/')
def index(handler):
    handler.finish('Hello rw.http')


@root.get('/lazy')
@gen.coroutine
def lazy(handler):
    yield gen.Task(tornado.ioloop.IOLoop.current().add_timeout, time.time())
    handler.finish('Hello lazy rw.http')


@root.post('/')
def root_submit(handler):
    handler.finish('root POST')


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
    root.render_template('index.html')
