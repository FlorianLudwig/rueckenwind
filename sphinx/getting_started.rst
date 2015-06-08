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
   And actually did: 0.3.x and 0.4.x are quite different.


Install
=======

Use pip::

  virtualenv my_playground
  . ./my_playground/bin/activate  
  pip install rueckenwind


Quick start
===========

It is highly recommended to develop and deploy within a `virtualenv <https://pypi.python.org/pypi/virtualenv>`_. Always.
So this documentation just assumes you do without further mentioning it.
After installing rückenwind you got a new command at your disposal: *rw*.
You can use it to generate a new rückendwind project skeleton::

  rw skel --name my_new_project

To start your new project::

  rw serv my_new_project.http

Go and visit `127.0.0.1:8000 <http://127.0.0.1:8000/>`_ to grab your *hello world* while it is hot.


Modules
=======

The most basic entity in rückenwind is a module. A rückenwind module
is a normal python module with some added convention.

The basic structure::

  module/
          __init__.py
          http.py
          static/
          templates/
          locale/
          

The obvious: all your static files go into the static/ folder and
your `jinja2 <http://jinja.pocoo.org/>`_ templates into
the templates/ folder.

The http.py must contain a Module named root.
It is the entry point for all http requests to your app.


.. note::

   Rückenwind does not try to be a framework for everyone and
   everything.  As one of the consequences only a single templating engine is supported.
   This keeps rückendwind code KISS. Don't like jinja? Sorry,
   rückenwind is not for you, switch to 
   `one of the many other frameworks <http://wiki.python.org/moin/WebFrameworks>`_.



Routing
=======

At the heart of rückenwind there is routing of http requests.
It draws inspiration from several other projects, like `Flask <http://flask.pocoo.org/>`_ .

.. note::

 * **HTTP methods** are strictly seperated. You cannot have one python function answering GET and POST.


An example RequestHandler

.. literalinclude:: my_playground/http.py


For details see: :doc:`www`

Templates
=========

For documentation about the Jinja templating engine please look at its beautiful `online documentation <http://jinja.pocoo.org/docs/>`_ .

Assigning variables::

  @root.get('/')
  def main(handler):
      handler['time'] = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
      root.finish(template='my_playground/index.html')


Within the template::

  The current time is {{ time }}.


If you refer to another resource there are two helper functions
for creating URIs. For static files use::

  {{ static('main.css') }}

This will insert an URI to your *main.css*, assuming there is one in your modules static folder.

If you want to link to another page there is::

  {{ url_for(handler.login) }}


Same routes as before::

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
