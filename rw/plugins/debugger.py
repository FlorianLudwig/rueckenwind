import datetime

import rw
import rw.www
from rw.www import RequestHandler, get
import rplug


class ExceptionFetcher(rplug.rw.ioloop_exception):
    def on_exception(self, exctype, value, exception, callback):
        rw.debug.save_current_traceback()


class ErrorTab(rplug.rw.infotab):
    def get_name(self):
        return 'Error'

    def get_content(self):
        return '<iframe src="/_p/rw.debugger/" width="100%" height="100%"></iframe>'


class Handler(RequestHandler):
    @get('/')
    def index(self):
        self['exceptions'] = rw.debug.EXCEPTIONS
        self['repr'] = repr
        self.finish(template='debugger/index.html')

    @get('/<num:int>')
    def show_tb(self, num):
        tb = rw.debug.EXCEPTIONS[num]
        html = tb.werkzeug_tb.render_full(evalex=True).encode('utf-8', 'replace')
        self.finish(html)


class HandlerPlug(rplug.rw.www):
    name = 'rw.debugger'
    handler = Handler


def activate():
    ExceptionFetcher.activate()
    ErrorTab.activate()
    HandlerPlug.activate()
