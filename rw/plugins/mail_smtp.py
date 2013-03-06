import smtplib
from email.mime.text import MIMEText

#from genshi import template
import rplug


#TPL_PATH = os.path.join('tpl', 'emails')
#TPL_LOADER = template.TemplateLoader(TPL_PATH, default_class=template.NewTextTemplate)
FROM = None
RELAY = 'localhost'
PORT = 0
USERNAME = None
PASSWORD = None
LOCAL_HOSTNAME = None
TLS = True


class SmtpMail(rplug.rw.email):
    def send(self, toaddrs, subject, body, attachments={}):
        """Send an email via smtp, all arguments must be utf-8 or unicode

           toaddrs is a list of receipients
        """
        if isinstance(body, unicode):
            body = body.encode('utf-8')
        if isinstance(subject, unicode):
            subject = subject.encode('utf-8')
        if isinstance(toaddrs, basestring):
            toaddrs = [toaddrs]
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['From'] = FROM
        msg['To'] = ','.join(toaddrs)
        msg['Subject'] = subject

        for fname, content in attachments.items():
            if isinstance(content, unicode):
                content = content.encode('utf-8')
            elif hasattr(content, 'read'):
                content = content.read()
            attachment = MIMEText(content)
            attachment.add_header('Content-Disposition', 'attachment', filename=fname)
            msg.attach(attachment)

        # The actual mail send
        s = smtplib.SMTP(RELAY, PORT, LOCAL_HOSTNAME)
        if TLS:
            s.ehlo()
            s.starttls()
            s.ehlo()
        if USERNAME:
            s.login(USERNAME, PASSWORD)
        s.sendmail(FROM, toaddrs, msg.as_string())
        s.quit()


def activate():
    SmtpMail.activate()
