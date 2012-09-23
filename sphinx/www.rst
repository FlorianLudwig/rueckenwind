Basic HTTP and Services
=======================

.. automodule:: rw.www

  .. autoclass:: RequestHandler

Request handlers
----------------
   
An example RequestHandler::

  class Registration(RequestHandler):
      @get('/')
      def register(self):
          self.finish(template='register.html')

      @post('/')
      def register_post(self):
          u = User(email= self.get_argument('email'),
                   username=self.get_argument('password'))
          self.redirect(url_fur(self.main))


  class Main(RequestHandler):
      @get('/')
      def main(self):
          self['time'] = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
          self.finish(template='index.html')

      @get('/entry/<id>')
      def entry(self, id):
          self['entries'] = get_entry_from_id(id)
          self.finish(template='main.html')

      mount('/register', Registration)
  
  
  
