Using MongoDB
=============

You can use any database with rueckenwind. But I like MongoDB for several reason, one being it does offer several options to use it asynchronously. After testing (and patching) several I decided to go with `motor <http://emptysquare.net/motor/>`_. As of writing it is still beta but well designed and actively developed. rw.db is what is rw.www to tornado just for motor: A collection of helpers to make my day-to-day work more comfortable.

.. automodule:: rw.db
