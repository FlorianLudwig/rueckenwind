.. _cfg:

Configuration Management
========================
For your convenience Rückenwind comes with simple (as in KISS) configuration management. When you start up your project Rückenwind will try to load its configuration and you might see logging like::

    rw[INFO] reading config: /my_virtualenv/src/my_cool_project_git/myproject/myproject.cfg
    rw[INFO] reading config: /etc/myproject.cfg
    rw[INFO] reading config: /home/joe/.myproject.cfg
    rw[INFO] reading config: /my_virtualenv/etc/myproject.cfg

The order the files appear is of importance. Values in the later overwrite values in the former. So you can specify
default values for your configuration values inside your project that gets overwritten by system wide configuration in
/etc that gets overwritten by user configuration in their homes that gets overwritten by configuratin inside your
virtual_envs /etc.

For example if your your project features the following config file::

    [mongodb]
    host = 127.0.0.1
    db = some_db

And your ~/.myproject.cfg is::

    [mongodb]
    host = db.local


You will get the following configuration dict::

    {'mongodb': {
        'host': 'db.local'
        'db': 'some_db'
    }}

Actually it is not a standard python dict but a `ConfigObj <http://www.voidspace.org.uk/python/configobj.html>`_ and therefor provides some extra methods like as_bool. It can be accessed via ``rw.cfg``. Please note that the dict gets populated when rw setups your project. So if you use::

    rw serv mycoolproject

The dict is populated before your module is loaded - meaning you can access ``rw.cfg`` without worries. In circumstances
were you are not running through the rw start command you might want to either use ``rw.setup('mycoolproject')`` to load
your module (which is what ``rw serv`` does). In other circumstances you might just want the config you can use:

.. autofunction:: rw.load_config



Design Decisions:
- JSON does not support comments
- ini is not strictly typed
