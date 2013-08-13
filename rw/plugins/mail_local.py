import os
import time
import cPickle

from mail import Mail
from rw.www import RequestHandler, get, post
import rplug

PATH = os.path.expanduser('~/.rw/')
DB_PATH = PATH + 'plugins.mail_local'


class LocalMail(rplug.rw.email):
    """rueckenwind email plugin for testing email functions during development"""
    def send(self, toaddrs, subject, body, attachments={}):
        print 'send message to', toaddrs.encode('utf-8')
        print 'Subject:', subject.encode('utf-8')
        print body
        if os.path.exists(DB_PATH):
            data = cPickle.load(open(DB_PATH))
        else:
            data = []
        data.append(Mail(toaddrs, subject, body, attachments))
        cPickle.dump(data, open(DB_PATH, 'w'))


class Handler(RequestHandler):
    @get('/')
    def index(self):
        if os.path.exists(DB_PATH):
            self['mails'] = cPickle.load(open(DB_PATH))
        else:
            self['mails'] = []
        self['repr'] = repr
        self.finish(template='local_mail/index.html')

    @post('/delete')
    def delete(self):
        mid = int(self.get_argument('mid'))
        data = cPickle.load(open(DB_PATH))
        if mid < len(data):
            del data[mid]
            cPickle.dump(data, open(DB_PATH, 'w'))
        self.redirect('/_p/rw.mail_local/')


class HandlerPlug(rplug.rw.www):
    name = 'rw.mail_local'
    handler = Handler


def activate():
    if not os.path.exists(PATH):
        os.makedirs(PATH)
    LocalMail.activate()
    HandlerPlug.activate()
