# Copyright 2012 Florian Ludwig
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sys
import traceback
import os
import logging

import tornado.ioloop
import tornado.web
import tornado.autoreload
from configobj import ConfigObj
import pkg_resources

import rbusys
rbusys.setup()
import rbus

from rw import testing


LOG = logging.getLogger(__name__)
DEBUG = True

MODULES = {'www': {},
           'rpc': {}}


def get_module(name, type='www', arg2=None, auto_load=True):
    if not name in MODULES[type]:
        if auto_load:
            mod = __import__(name + '.' + type)
            if '.' in name:
                for sub_name in name.split('.')[1:]:
                    mod = getattr(mod, sub_name)
            MODULES[type][name] = mod
        else:
            raise AttributeError('%s.%s is not loaded and auto_load=False' % (name, type))
        # app = MODULES[type][name].www.Main
        # assert issubclass(app, RequestHandler), repr(app) + ' is not a subclass of rw.RequestHandler'
    return MODULES[type][name]


def load(name):
    main_module = __import__(name, globals(), {}, [name[:-name.rfind('.')]])
    assert main_module.__name__ == name
    for rw_module in ['www']:
        try:
            mod = __import__(name + '.' + rw_module, globals(), {}, [rw_module])
            __import__('rw.' + rw_module, globals(), {}, [rw_module]).load(mod)
        except ImportError:
            # TODO: if the module we try to import exists
            #       but fails to load because within it
            #       an ImportError is raised this error
            #       is silented here. Bad.
            continue
    return main_module


def drop_privileges(uid_name='nobody', gid_name=None):
    import pwd
    import grp
    # get uid/gid from the name
    uid = pwd.getpwnam(uid_name).pw_uid
    if gid_name is None:
        # on some linux systems the group of nobody is called
        # nobody (e.g. Fedora) on some it is nogroup (e.g. Debian)
        for gid_name in ('nobody', 'nogroup'):
            try:
                gid = grp.getgrnam(gid_name).gr_gid
                break
            except KeyError:
                pass
        else:
            raise KeyError('Cannot change group, group of "nobody" is unknown')
    else:
        gid = grp.getgrnam(gid_name).gr_gid

    # remove group privileges
    os.setgroups([])

    # set new uid/gid
    os.setgid(gid)
    os.setuid(uid)

    # Ensure a very conservative umask
    os.umask(077)


class RWIOLoop(tornado.ioloop.IOLoop):
    def handle_callback_exception(self, callback):
        exctype, value, exception = sys.exc_info()
        if issubclass(exctype, testing.StopIOLoop):
            raise
        traceback.print_exception(exctype, value, exception)
        try:
            rbus.rw.ioloop_exception.on_exception(exctype, value, exception, callback)
        except testing.StopIOLoop, e:
            self.stop()
            raise e
        except:
            print 'ERROR calling exception handler'
            exctype, value, exception = sys.exc_info()
            traceback.print_exception(exctype, value, exception)

io_loop = tornado.ioloop.IOLoop._instance = RWIOLoop()


def update_config(cfg, update):
    for key, value in update.items():
        if key in cfg and isinstance(value, dict):
            update_config(cfg[key], value)
        else:
            cfg[key] = value


class ConfigHandler(object):
    """Handling Configuration.

    Design Decisions:
     - JSON does not support comments
     - YAML got some smaller problems but so does ini. In the end a KISS decision was made.
    """
    def __getattr__(self, item):
        cfg_name = item + '.cfg'
        CONFIG_FILES = [pkg_resources.resource_filename(item, 'config.cfg')]
        CONFIG_FILES += ['/etc/' + cfg_name, os.path.expanduser('~/.')  + cfg_name]
        if 'VIRTUAL_ENV' in os.environ:
            CONFIG_FILES.append(os.environ['VIRTUAL_ENV'] + '/etc/' + cfg_name)

        # read config
        config = {}
        for config_path in CONFIG_FILES:
            if os.path.exists(config_path):
                LOG.info('reading config: ' + config_path)
                config_obj = ConfigObj(config_path)
                update_config(config, config_obj)
            else:
                LOG.debug('config does not exist: ' + config_path)

        setattr(self, item, config)
        return config

cfg = ConfigHandler()


def setup(app_name, type='www', address=None, port=None):
    mod = getattr(__import__('rw.' + type), type)
    return mod.setup(app_name, address=address, port=port)


def start(app=None, type='www', **kwargs):
    if not app is None:
        setup(app, type, **kwargs)

    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print 'ctrl+c received. Exiting'
