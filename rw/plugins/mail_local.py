import os
import time
import cPickle

from rw.www import RequestHandler, get, post
from mail import Mail
import rplug

PATH = os.path.expanduser('~/.rw/')
DB_PATH = PATH + 'plugins.mail_local'


class LocalMail(rplug.rw.email):
    def send(self, toaddrs, subject, body):
        print 'send message to', toaddrs, subject, body
        if os.path.exists(DB_PATH):
            f = open(DB_PATH)
            data = cPickle.load(f)
            f.close()
        else:
            data = []
        data.append(Mail(toaddrs, subject, body))
        f = open(DB_PATH, 'w')
        cPickle.dump(data, f)
        f.close()


class MailTab(rplug.rw.infotab):
    def get_name(self):
        return 'Mail'

    def get_content(self):
        return '<iframe src="/_p/rw.mail_local/" width="100%" height="100%"></iframe>'


class Handler(RequestHandler):
    @get('/')
    def index(self):
        if os.path.exists(DB_PATH):
            f = open(DB_PATH)
            self['mails'] = cPickle.load(f)
            f.close()
        else:
            self['mails'] = []
        self['repr'] = repr
        self.finish(template='local_mail/index.html')

    @post('/delete')
    def delete(self):
        mid = int(self.get_argument('mid'))
        f = open(DB_PATH)
        data = cPickle.load(f)
        f.close()
        if mid < len(data):
            del data[mid]
            f = open(DB_PATH, 'w')
            cPickle.dump(data, f)
            f.close()
        self.redirect('/_p/rw.mail_local/')


class HandlerPlug(rplug.rw.www):
    name = 'rw.mail_local'
    handler = Handler


def activate():
    if not os.path.exists(PATH):
        os.makedirs(PATH)
    LocalMail.activate()
    MailTab.activate()
    HandlerPlug.activate()
