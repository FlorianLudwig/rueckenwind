# Copyright 2012-2013 Florian Ludwig
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
import select
from tornado import gen, concurrent

import tornado.ioloop
import tornado.web
import tornado.autoreload
from configobj import ConfigObj
import pkg_resources

import rbusys
rbusys.setup()
import rbus
import rplug

from rw import testing


LOG = logging.getLogger(__name__)
DEBUG = True

MODULES = {'www': {},
           'rpc': {}}

cfg = {}


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
        except Exception:
            print 'ERROR calling exception handler'
            exctype, value, exception = sys.exc_info()
            traceback.print_exception(exctype, value, exception)


def rw_ioloop_instance():
    if hasattr(select, "epoll"):
        from tornado.platform.epoll import EPollIOLoop

        class RWEPollIOLoop(RWIOLoop, EPollIOLoop):
            pass

        return RWEPollIOLoop()
    if hasattr(select, "kqueue"):
        # Python 2.6+ on BSD or Mac
        from tornado.platform.kqueue import KQueueIOLoop

        class KQueueIOLoop(RWIOLoop, KQueueIOLoop):
            pass

        return KQueueIOLoop()
    from tornado.platform.select import SelectIOLoop

    class RWSelectIOLoop(RWIOLoop, SelectIOLoop):
        pass

    return RWSelectIOLoop()


io_loop = tornado.ioloop.IOLoop._instance = rw_ioloop_instance()


def update_config(cfg, update):
    for key, value in update.items():
        if key in cfg and isinstance(value, dict):
            update_config(cfg[key], value)
        else:
            cfg[key] = value


def load_config(module_name, extra_files=None):
    """Load configuration for given module and return config dict


     """
    if isinstance(extra_files, basestring):
        extra_files = [extra_files]
    cfg_name = module_name + '.cfg'
    CONFIG_FILES = [pkg_resources.resource_filename(module_name, cfg_name)]
    CONFIG_FILES += ['/etc/' + cfg_name, os.path.expanduser('~/.')  + cfg_name]
    if 'VIRTUAL_ENV' in os.environ:
        CONFIG_FILES.append(os.environ['VIRTUAL_ENV'] + '/etc/' + cfg_name)
    if extra_files:
        CONFIG_FILES.extend(extra_files)
    # read config
    config = {}
    for config_path in CONFIG_FILES:
        if os.path.exists(config_path):
            LOG.info('reading config: ' + config_path)
            config_obj = ConfigObj(config_path)
            update_config(config, config_obj)
        else:
            LOG.debug('config does not exist: ' + config_path)

    return ConfigObj(config)


class RWModuleSetup(rplug.rw.module):
    setup_mods = []

    def start(self):
        for typ, app_name, address, port in TO_SETUP:
            if not isinstance(typ, basestring):
                raise AttributeError('typ must be string. type = {}'.format(repr(typ)))
            mod = getattr(__import__('rw.' + typ), typ).Module()
            mod.setup(app_name, address=address, port=port)
            self.setup_mods.append(mod)

    @gen.coroutine
    def shutdown(self):
        while self.setup_mods:
            mod = self.setup_mods.pop()
            mod.shutdown()


class RWPluginLoad(rplug.rw.module):
    @gen.coroutine
    def setup(self):
        futures = []
        for plugin in cfg.get('rw.plugins', {}):
            if not cfg['rw.plugins'].as_bool(plugin):
                continue
            plugin_mod = __import__(plugin)
            for part in plugin.split('.')[1:]:
                plugin_mod = getattr(plugin_mod, part)
            futures.append(plugin_mod.activate())
        futures = [future for future in futures if isinstance(future, gen.Future)]
        if futures:
            yield futures



RWModuleSetup.activate()
RWPluginLoad.activate()
TO_SETUP = []


def setup(app_name, typ='www', extra_config_files=None, address=None, port='8000+'):
    """setup rueckenwind app"""
    cfg.update(load_config(app_name, extra_config_files))
    TO_SETUP.append((typ, app_name, address, port))


def start(app=None, type='www', **kwargs):
    """Start rueckenwind app"""
    if not app is None:
        setup(app, type, **kwargs)

    io_loop = tornado.ioloop.IOLoop.current()
    io_loop.add_callback(_start)

    if DEBUG:
        tornado.autoreload.start()

    try:
        io_loop.start()
    except KeyboardInterrupt:
        print 'ctrl+c received. Exiting'

    io_loop.run_sync(_shutdown)


def run(func):
    """run coroutine sync within rw context"""
    io_loop = tornado.ioloop.IOLoop.current()

    @gen.coroutine
    def runner():
        yield _start()
        result = func()
        if isinstance(result, concurrent.Future):
            yield result

    try:
        io_loop.run_sync(runner)
    except KeyboardInterrupt:
        print 'ctrl+c received. Exiting'

    io_loop.run_sync(_shutdown)


@gen.coroutine
def _shutdown():
    LOG.info('entering shutdown phase')
    shutdown = rbus.rw.module.shutdown()
    futures = [future for future in shutdown if isinstance(future, concurrent.Future)]
    if futures:
        yield futures


@gen.coroutine
def _start():
    # phase 1, pre setup
    try:
        LOG.info('entering setup phase')
        starting = rbus.rw.module.setup()
        futures = [future for future in starting if isinstance(future, concurrent.Future)]
        if futures:
            yield futures

        # start
        LOG.info('entering start phase')
        starting = rbus.rw.module.start()
        futures = [future for future in starting if isinstance(future, concurrent.Future)]
        if futures:
            yield futures

        # post_setup
        LOG.info('entering post_start phase')
        starting = rbus.rw.module.post_start()
        futures = [future for future in starting if isinstance(future, concurrent.Future)]
        if futures:
            yield futures
        # and we are done.
    except Exception as e:
        LOG.error('startup failed')
        import traceback
        traceback.print_exc()
        io_loop.stop()
