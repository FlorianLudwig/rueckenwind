# Copyright 2014 Florian Ludwig
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

import logging

import tornado.gen

from . import event


LOG = logging.getLogger(__name__)

PHASE_CONFIGURATION = event.Event('PHASE_CONFIGURATION')
PHASE_SETUP = event.Event('PHASE_SETUP')
PHASE_START = event.Event('PHASE_START')
PHASE_POST_START = event.Event('PHASE_POST_START')


@tornado.gen.coroutine
def start():
    LOG.info('server startup: configuration phase')
    yield PHASE_CONFIGURATION()
    LOG.info('server startup: setup phase')
    yield PHASE_SETUP()
    LOG.info('server startup: start phase')
    yield PHASE_START()
    LOG.info('server startup: post start phase')
    yield PHASE_POST_START()
    LOG.info('server startup done')
    