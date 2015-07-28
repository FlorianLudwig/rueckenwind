import rw.websocket

import rw.http
from rw import gen


class WebSocketHandler(rw.websocket.WebSocketHandler):
    @gen.engine
    def open(self):
        print 'open'

    @gen.engine
    def on_message(self, message):
        print 'on message'

    @gen.engine
    def on_close(self):
        print 'on close'

    def __del__(self):
        # XXX debugging
        print 'bye bye'


root = rw.http.Module('websocket')
root.mount('/ws', WebSocketHandler)


@root.get('/')
def index():
    root.render_template('index.html')
