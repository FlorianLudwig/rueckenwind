from __future__ import absolute_import
import rplug
import elixir


class ExceptionFetcher(rplug.rw.ioloop_exception):
    def on_exception(self, exctype, value, exception, callback):
        elixir.session.rollback()


def activate():
    ExceptionFetcher.activate()
