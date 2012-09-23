import sys
import urllib
import StringIO

import tornado.ioloop
import tornado.web
import werkzeug.debug
from werkzeug.debug.tbtools import get_current_traceback


class DebugRequestHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        tornado.web.RequestHandler.__init__(self, *args, **kwargs)
        self._tracebacks = {}
        self._frames = {}

    def get_error_html(self, status_code, **kwargs):
        if 'exception' in kwargs:
            print self.application

            return self.application.get_error_html(status_code, **kwargs)
        else:
            return tornado.web.RequestHandler.get_error_html(status_code, **kwargs)


class WSGIHandler(tornado.web.RequestHandler):
    """Based on http://paste.plurk.com/show/18554/"""
    def __init__(self, application, request, wsgi_app):
        self.wsgi_app = wsgi_app
        tornado.web.RequestHandler.__init__(self, application, request)
        self._transforms = []

    def delegate(self):
        env = self.make_wsgi_environ(self.request)
        out = self.wsgi_app(env, self._start_response)

        if not (hasattr(out, 'next') or isinstance(out, list)):
            out = [out]

        # don't send any data for redirects
        if self._status_code not in [301, 302, 303, 304, 307]:
            for x in out:
                self.write(x)
                print 'writing'
        else:
            print 'not sending any data, code', self._status_code

    get = post = put = delete = delegate

    def _start_response(self, status, headers, exc_info=None):
        status_code = int(status.split()[0])
        self.set_status(status_code)
        for name, value in headers:
            self.set_header(name, value)

    def make_wsgi_environ(self, request):
        """Makes wsgi environment using HTTPRequest"""
        env = {}
        env['REQUEST_METHOD'] = request.method
        env['SCRIPT_NAME'] = ""
        env['PATH_INFO'] = urllib.unquote(request.path)
        env['QUERY_STRING'] = request.query

        special = ['CONTENT_LENGTH', 'CONTENT_TYPE']

        for k, v in request.headers.items():
            k =  k.upper().replace('-', '_')
            if k not in special:
                k = 'HTTP_' + k
            env[k] = v

        env["wsgi.url_scheme"] = request.protocol
        env['REMOTE_ADDR'] = request.remote_ip
        env['HTTP_HOST'] = request.host
        env['SERVER_PROTOCOL'] = request.version

        if request.body:
            env['wsgi.input'] = StringIO.StringIO(request.body)

        env['wsgi.errors'] = sys.stderr
        env['wsgi.multithread'] = False
        env['wsgi.multiprocess'] = False
        env['wsgi.run_once'] = False

        return env


class DebugApplication(tornado.web.Application):
    def __init__(self, *args, **kwargs):
        def FakeWSGIApp(env, start_response):
            start_response('200 OK', [])
            return []
        self._debugger_app = werkzeug.debug.DebuggedApplication(FakeWSGIApp, evalex=True)
        tornado.web.Application.__init__(self, *args, **kwargs)

    def  __call__(self, request):
        print 'call to debug app'
        if '__debugger__' in request.uri:
            print 'blubb'
            handler = WSGIHandler(self, request, self._debugger_app)
            handler.delegate()
            handler.finish()
        return tornado.web.Application.__call__(self, request)

    def get_error_html(self, status_code, **kwargs):
            traceback = get_current_traceback(skip=1, show_hidden_frames=False,
                                              ignore_system_exceptions=True)
            for frame in traceback.frames:
                self._debugger_app.frames[frame.id] = frame
            self._debugger_app.tracebacks[traceback.id] = traceback
            return traceback.render_full(evalex=True).encode('utf-8', 'replace')

