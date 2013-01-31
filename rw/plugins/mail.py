import time
class Mail(object):
    def __init__(self, toaddrs, subject, body):
        self.toaddrs = toaddrs
        self.subject = subject
        self.body = body
        self.time = time.time()