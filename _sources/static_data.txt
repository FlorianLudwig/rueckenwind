.. _getting_started:


**************
Static Content
**************

You probably got content that is for every user the same on every request. Typically this is content like images, css or javascript. Downloads (as in content that is not directly dispalyed fron html) or for this matter large files in generall should treated a little different.

You probably remember that there is a function called "static" to refer to your
static content::

  {{ static('main.css') }}

The url it generates looks something like this::

  /static/simpleblog/main.css?v=a37b


All static content is below /static/. Followed by the modules name (simpleblog here). Appended is version string to ensure the browser got the right thing in its cache. The version is the first few bytes of the hexdecimal representation of the md5 of the content of the main.css.


Dynamic Static Content
======================

The definition of "static content" in rückenwind is content that is the same on every request for every user.

Deployment
==========


