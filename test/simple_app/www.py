from rw.www import RequestHandler, post


class Main(RequestHandler):
    @post('/')
    def index(self):
        self.finish(template='index.html')
