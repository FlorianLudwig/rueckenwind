import tornado.gen

from . import event


PHASE_CONFIGURATION = event.Event()
PHASE_SETUP = event.Event()
PHASE_START = event.Event()
PHASE_POST_START = event.Event()


@tornado.gen.coroutine
def start():
    yield PHASE_CONFIGURATION()
    yield PHASE_SETUP()
    yield PHASE_START()
    yield PHASE_POST_START()