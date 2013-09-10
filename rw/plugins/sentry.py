# -*- coding: utf-8 -*-
from raven.contrib.tornado import AsyncSentryClient, SentryMixin
import rplug
import rw
import rw.www
from tornado.web import HTTPError

SENTRY_CLIENT = None


class SentryMixinRW(SentryMixin):
    def __init__(self):
        super(SentryMixinRW, self).__init__()
        self.request = None

    def get_sentry_client(self):
        return SENTRY_CLIENT

    def get_sentry_user_info(self):
        return {
            'sentry.interfaces.User': {}
        }

    def _capture(self, call_name, data=None, **kwargs):
        if self.request:
            return super(SentryMixinRW, self)._capture(call_name, data, **kwargs)
        else:
            client = self.get_sentry_client()

        return getattr(client, call_name)(data=data, **kwargs)


class ExceptionFetcher(SentryMixinRW, rplug.rw.ioloop_exception):
    def on_exception(self, exctype, value, exception, callback):
        if isinstance(exception, HTTPError) and exception.status_code == 404:
            # we don't capture 404 "errors"
            return
        current_handler = rw.www.current_handler()
        if current_handler:
            self.request = current_handler.request
        self.captureException(exc_info=(exctype, value, exception))


def activate():
    global SENTRY_CLIENT
    SENTRY_CLIENT = AsyncSentryClient(rw.cfg['rw.plugins.sentry']['dsn'])
    ExceptionFetcher.activate()