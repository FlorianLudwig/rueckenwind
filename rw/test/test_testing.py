"""Let's test the testing framework"""

import pytest

from tornado import ioloop
from rw import testing

def test_stopioloop():
    def lets_crash():
        raise testing.StopIOLoop()
    loop = ioloop.IOLoop.instance()
    loop.add_timeout(1, lets_crash)
    with pytest.raises(testing.StopIOLoop):
        loop.start()