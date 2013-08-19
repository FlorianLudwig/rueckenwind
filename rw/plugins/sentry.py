# -*- coding: utf-8 -*-
from raven.contrib.tornado import AsyncSentryClient, SentryMixin
import rplug
import rw
import rw.www

SENTRY_CLIENT = None


class SentryMixinRW(SentryMixin):
    def get_sentry_client(self):
        return SENTRY_CLIENT

    def get_sentry_user_info(self):
        return {
            'sentry.interfaces.User': {}
        }


class ExceptionFetcher(SentryMixinRW, rplug.rw.ioloop_exception):
    def on_exception(self, exctype, value, exception, callback):
        self.request = rw.www.current_handler().request
        self.captureException(exc_info=(exctype, value, exception))


def activate():
    global SENTRY_CLIENT
    SENTRY_CLIENT = AsyncSentryClient(rw.cfg['rw.plugins.sentry']['url'])
    ExceptionFetcher.activate()

