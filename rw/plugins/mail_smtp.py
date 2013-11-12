from email.mime.base import MIMEBase
import mimetypes
import smtplib
import copy
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

#from genshi import template
import rplug
import rw

#TPL_PATH = os.path.join('tpl', 'emails')
#TPL_LOADER = template.TemplateLoader(TPL_PATH, default_class=template.NewTextTemplate)


class SmtpMail(rplug.rw.email):
    def send(self, toaddrs, subject, body, attachments={}):
        """Send an email via smtp, all arguments must be utf-8 or unicode

           toaddrs is a list of receipients
        """
        print 'send mail!'
        if isinstance(body, unicode):
            body = body.encode('utf-8')
        if isinstance(subject, unicode):
            subject = subject.encode('utf-8')
        if isinstance(toaddrs, basestring):
            toaddrs = [toaddrs]
        if isinstance(body, (MIMEText, MIMEMultipart)):
            msg = copy.copy(body)
        else:
            msg = MIMEText(body, 'plain', 'utf-8')
        if 'From' not in msg:
            msg['From'] = rw.cfg['mail']['from']
        if 'To' not in msg:
            msg['To'] = ','.join(toaddrs)
        if 'Subject' not in msg:
            msg['Subject'] = subject

        for fname, content in attachments.items():
            if isinstance(content, unicode):
                content = content.encode('utf-8')
            elif hasattr(content, 'read'):
                content = content.read()
            mimetype = mimetypes.guess_type(fname)[0]
            if mimetype is None:
                mimetype = 'application/octet-stream'
            attachment = MIMEBase(*mimetype.split('/'))
            attachment.set_payload(content)
            email.Encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', 'attachment', filename=fname)
            msg.attach(attachment)

        # The actual mail send
        s = smtplib.SMTP(rw.cfg['mail']['relay'],
                         int(rw.cfg['mail'].get('port', 0)),
                         rw.cfg['mail'].get('local_hostname', None))
        print type(rw.cfg['mail']['tls'])
        if rw.cfg['mail']['tls']:
            s.starttls()
            s.ehlo()
        if 'username' in rw.cfg['mail']:
            s.login(rw.cfg['mail']['username'],
                    rw.cfg['mail'].get('password', ''))
        s.sendmail(rw.cfg['mail']['from'], toaddrs, msg.as_string())
        s.quit()


def activate():
    SmtpMail.activate()
