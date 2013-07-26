from __future__ import absolute_import

import rw
import rplug
import elixir
from sqlalchemy import create_engine


class ExceptionFetcher(rplug.rw.ioloop_exception):
    def on_exception(self, exctype, value, exception, callback):
        elixir.session.rollback()


def activate():
    cfg = rw.cfg['mysql']
    uri = 'mysql://%s:%s@%s/%s' % (cfg['user'], cfg['password'], cfg['host'], cfg['db'])
    engine = create_engine(uri, pool_size=1, pool_recycle=3600, echo=False)
    elixir.metadata.bind = engine
    ExceptionFetcher.activate()
