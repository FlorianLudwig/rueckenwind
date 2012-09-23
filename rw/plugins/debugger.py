import datetime

import rw
import rw.www
from rw.www import RequestHandler, get
import rplug
from werkzeug.debug import tbtools

#PATH = os.path.expanduser('~/.rw/')
#DB_PATH = PATH + 'plugins.mail_local'
EXCEPTIONS = []


class CapturedException(object):
    def __init__(self, exctype, value, exception, callback):
        self.datetime = datetime.datetime.now()
        self.exctype = exctype
        self.value = value
        self.exception = exception
        self.callback = callback
        self.werkzeug_tb = tbtools.Traceback(exctype, value, exception)

    def __cmp__(self, o):
        return cmp(self.datetime, o.datetimes)


class ExceptionFetcher(rplug.rw.ioloop_exception):
    def on_exception(self, exctype, value, exception, callback):
        tb = CapturedException(exctype, value, exception, callback)
        EXCEPTIONS.append(tb)
        for frame in tb.werkzeug_tb.frames:
            rw.www.BASE_APP._debugger_app.frames[frame.id] = frame
        rw.www.BASE_APP._debugger_app.tracebacks[tb.werkzeug_tb.id] = tb.werkzeug_tb


class ErrorTab(rplug.rw.infotab):
    def get_name(self):
        return 'Error'

    def get_content(self):
        return '<iframe src="/_p/rw.debugger/" width="100%" height="100%"></iframe>'


class Handler(RequestHandler):
    @get('/')
    def index(self):
        self['exceptions'] = EXCEPTIONS
        self['repr'] = repr
        self.finish(template='debugger/index.html')

    @get('/<num:int>')
    def show_tb(self, num):
        tb = EXCEPTIONS[num]
        html = tb.werkzeug_tb.render_full(evalex=True).encode('utf-8', 'replace')
        self.finish(html)


class HandlerPlug(rplug.rw.www):
    name = 'rw.debugger'
    handler = Handler


def activate():
    ExceptionFetcher.activate()
    ErrorTab.activate()
    HandlerPlug.activate()

