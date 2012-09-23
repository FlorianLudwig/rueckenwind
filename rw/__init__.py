import sys
import re
import traceback
import argparse
import os
import pwd
import grp

import tornado.ioloop
import tornado.web
import tornado.autoreload

import rbusys
rbusys.setup()
import rbus


DEBUG = True

MODULES = {'www': {},
           'rpc': {}}

APPS = {}


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



purge_line = re.compile(' line [0-9]*,')

ERROR_PATH = '/error path not set/'


class RWIOLoop(tornado.ioloop.IOLoop):
    #def handle_callback_exception(self, callback):
    #    """This method is called whenever a callback run by the IOLoop
    #    throws an exception.
    #
    #    The exception itself is not passed explicitly, but is available
    #    in sys.exc_info.
    #    """
    #    t = traceback.format_exc()
    #    error_id = hashlib.md5(purge_line.sub('', t)).hexdigest()
    #    fname = ERROR_PATH + '/' + error_id
    #    if not os.path.exists(fname):
    #        open(fname, 'w').write(t)
    #
    #    open(fname, 'a').write(time.strftime("%Y-%m-%d (%a) %H:%M:%S\n"))
    #    logging.error(t)

    def handle_callback_exception(self, callback):
        exctype, value, exception = sys.exc_info()
        traceback.print_exception(exctype, value, exception)
        try:
            rbus.rw.ioloop_exception.on_exception(exctype, value, exception, callback)
        except:
            print 'ERROR calling exception handler'
            exctype, value, exception = sys.exc_info()
            traceback.print_exception(exctype, value, exception)
        #if DEBUG:
        #    rbus.rw.
        #    html = debug_handler.get_error_html(500, exception=True)
        #    page = str(int(time.time()))
        #    MainHandler.pages[page] = str(html)
        #    url = 'http://127.0.0.1:8888/?page=' + page
        #    logging.error('Debug via: ' + url)
        #    webbrowser.open(url)
        #else:
        #    fname = 'errors/%s' % time.strftime('%Y-%m-%d_%H.%M.%S')
        #    open(fname, 'w').write(traceback.format_exc())

io_loop = tornado.ioloop.IOLoop._instance = RWIOLoop()


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


