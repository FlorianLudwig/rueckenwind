import time

import rw.http
import rw.gen


registration = rw.http.Module('my_playground')


@registration.get('/')
def register(handler):
    handler.render_template(template='register.html')


@registration.post('/')
def register_post(handler):
    u = User(email=handler.get_argument('email'),
             username=handler.get_argument('password'))
    handler.redirect(url_for(main))


root = rw.http.Module('my_playground')


@root.get('/')
def main(handler):
    handler['time'] = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
    root.render_template('index.html')


@root.get('/entry/<id>')
@rw.gen.coroutine
def entry(self, id):
    self['entries'] = yield get_entry_from_id(id)
    self.finish(template='my_playground/main.html')


root.mount('/register', registration)
