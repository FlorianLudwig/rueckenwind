from rw.www import RequestHandler, get, post


class Main(RequestHandler):
    @get('/')
    def index(self):
        self.finish(template='index.html')
