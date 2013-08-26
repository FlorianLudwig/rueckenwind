# -*- coding: utf-8 -*-
import os
import time
import cPickle
import chardet
from email.mime.multipart import MIMEMultipart
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
            mails = cPickle.load(open(DB_PATH))
            self['mails'] = []
            for i, m in enumerate(mails):
                if isinstance(m.toaddrs, str):
                    m.toaddrs = m.toaddrs.decode('utf-8')
                if isinstance(m.subject, str):
                    m.subject = m.subject.decode('utf-8')
                entry = {'toaddrs': m.toaddrs, 'subject': m.subject}
                if isinstance(m.body, MIMEMultipart):
                    html = None
                    for j, part in enumerate(m.body.get_payload()):
                        if part.get_content_charset() is None:
                            charset = chardet.detect(str(part))['encoding']
                        else:
                            charset = part.get_content_charset()
                        if part.get_content_type() == 'text/plain':
                            entry['text'] = unicode(part.get_payload(decode=True), str(charset), "ignore")
                        elif part.get_content_type() == 'text/html':
                            entry['html_id'] = i
                            entry['html_part'] = j
                elif isinstance(m.body, unicode):
                    entry['text'] = m.body
                else:
                    entry['text'] = unicode(m.body.get_payload(decode=True), m.body.get_content_charset(),
                                            'ignore')
                self['mails'].append(entry)
        else:
            self['mails'] = []
        self['repr'] = repr
        self.finish(template='local_mail/index.html')

    @get('/html/<_id:int>/<part:int>')
    def html_content(self, _id, part):
        if os.path.exists(DB_PATH):
            mails = cPickle.load(open(DB_PATH))
            mail_part = mails[_id].body.get_payload()[part]
            if mail_part.get_content_charset() is None:
                charset = chardet.detect(str(part))['encoding']
            else:
                charset = mail_part.get_content_charset()
            html = unicode(mail_part.get_payload(decode=True), str(charset), "ignore")
            self.finish(html)

    @post('/delete')
    def delete(self):
        mid = int(self.get_argument('mid'))
        data = cPickle.load(open(DB_PATH))
        if mid < len(data):
            del data[mid]
            cPickle.dump(data, open(DB_PATH, 'w'))
        self.redirect('/_p/rw.mail_local/')

    @get('/json/count')
    def count_json(self):
        count = 0
        if os.path.exists(DB_PATH):
            mails = cPickle.load(open(DB_PATH))
            count = len(mails)
        self.finish({'count': count})


class HandlerPlug(rplug.rw.www):
    name = 'rw.mail_local'
    handler = Handler


def activate():
    if not os.path.exists(PATH):
        os.makedirs(PATH)
    LocalMail.activate()
    HandlerPlug.activate()
