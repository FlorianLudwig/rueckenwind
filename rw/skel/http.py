"""An example using as many different features of rueckenwind as possible

"""
import rw.http
from rw import gen


root = rw.http.Module('{{name}}')


@root.get('/')
def index(handler):
    root.render_template('index.html')
