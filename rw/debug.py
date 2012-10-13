# Copyright 2012 Florian Ludwig
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sys
import urllib
import StringIO
import datetime

import tornado.ioloop
import tornado.web
import werkzeug.debug
from werkzeug.debug.tbtools import get_current_traceback, Traceback


def FakeWSGIApp(env, start_response):
    start_response('200 OK', [])
    return ['Interpreter frame not found. '
            'Either the server restarted and the frame is lost '
            'or you triggered a bug in rw itself. Sorry.']

DEBUG_APP = werkzeug.debug.DebuggedApplication(FakeWSGIApp, evalex=True)
EXCEPTIONS = []


class CapturedException(object):
    def __init__(self, tb):
        self.datetime = datetime.datetime.now()
        self.werkzeug_tb = tb

    def __cmp__(self, o):
        return cmp(self.datetime, o.datetimes)


def save_current_traceback():
    traceback = get_current_traceback(skip=1, show_hidden_frames=False,
                                      ignore_system_exceptions=True)
    for frame in traceback.frames:
        DEBUG_APP.frames[frame.id] = frame
    DEBUG_APP.tracebacks[traceback.id] = traceback
    EXCEPTIONS.append(CapturedException(traceback))
    return traceback


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
            k = k.upper().replace('-', '_')
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
    def  __call__(self, request):
        if '__debugger__' in request.uri:
            handler = WSGIHandler(self, request, DEBUG_APP)
            handler.delegate()
            handler.finish()
        return tornado.web.Application.__call__(self, request)

    def get_error_html(self, status_code, **kwargs):
            traceback = save_current_traceback()
            return traceback.render_full(evalex=True).encode('utf-8', 'replace')
