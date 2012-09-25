.. _getting_started:


***************
Getting started
***************

.. _installing-docdir:


Design Principles and Goals
===========================

 * **KISS**
   Keept it simple, stupid.
 * **Convention over configuration**
   But don't take it too far.
 * **Reusablity**
   I will not repeat myself.
 * **Don't try to please everyone**

.. note::

   Rückenwind is in **alpha** stage of development, backwards compatibility will break.


Install
=======

Use pip::

  virtualenv --distribute my_playground
  . ./my_playground/bin/activate  
  pip install -e git@github.com:FlorianLudwig/rueckenwind.git#egg=rueckenwind


Quick start
===========

After installing rückenwind you got a new command at your disposal: *rw*.
You can use it to generate a new rückendwind project skelton::

  rw skel --name my_new_project

To start your new project::

  rw serv my_new_project

Go and visit `127.0.0.1:8000 <http://127.0.0.1:8000/>`_ to grab your *hello world* while it is hot.


Modules
=======

The most basic entity in rückenwind is a module. A rückenwind module
is a normal python module with some added convention.

The basic structure::

  module/
          __init__.py
          www.py
          static/
          templates/
          locale/
          

The obvious: all your static files go into the static/ folder and
your `jinja2 <http://jinja.pocoo.org/>`_ templates into
the templates/ folder.

The www.py must contain a class named Main that derives from rw.RequestHandler.
It is the entry point for all http requests to this module.


.. note::

   Rückenwind does not try to be a framework for everyone and
   everything. As one of the consequenes only a single templateing engine is supported.
   This keeps rückendwind code KISS. Don't like jinja? Sorry,
   rückenwind is not for you, switch to 
   `one of the many other frameworks <http://wiki.python.org/moin/WebFrameworks>`_.



Routing
=======

At the heard of rückenwind there is routing of http requests. It draws insparation from several other projects, like `Flask <http://flask.pocoo.org/>`_ .

Design notes

 * **Classes** are used to allow request handlers to be reused via inheritance.
 * **HTTP methods** are strictly seperated. You cannot have one python function answering GET and POST.


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

For details see: :doc:`www`

Templates
=========

For documentation about the Jinja templating engine please look at its beautiful `online documentation <http://jinja.pocoo.org/docs/>`_ .

Assigning variables::

  class Main(RequestHandler):
      @get('/')
      def main(self):
          self['time'] = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
          self.finish(template='index.html')


Within the template::

  The current time is {{ time }}.


If you refer to another resource there are two helper functions
for creating URIs. For static files use::

  {{ static('main.css') }}

This will insert an URI to your *main.css*, assuming there is one in your modules static folder.

If you want to link to another page there is::

  {{ url_for(handler.login) }}

Some more examples, same routes as before::

  class Main(RequestHandler):
      @get('/')
      def main(self):
          # ...

      @get('/register')
      def register(self):
          # ...

      @get('/entry/<id>')
      def entry(self, id):
          # ...


============================  ========
command                       result
============================  ========
url_for(handler.login)        /
url_for(handler.register)     /register
url_for(handler.entry, id=1)  /entry/1
============================  ========
