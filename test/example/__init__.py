"""An example using as many different features of rueckenwind as possible

"""
import rw.testing
import rw.http
import rw.httpbase

root = rw.http.Module('test.example')


@root.init
def init():
    root.template_env.globals['static_value'] = 42


@root.get('/')
def index(handler):
    handler.finish('Hello rw.http')


@root.post('/')
def root_submit(handler):
    handler.finish('root POST')


@root.get('/user/<name>')
def root_submit(handler, name):
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
    root.render_template('index.html.jj2')
