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

"""Load yaml based configuration"""
from __future__ import absolute_import, division, print_function, with_statement

import os
import pkg_resources
import logging

import tornado.autoreload
import yaml


LOG = logging.getLogger(__name__)


def read_file(paths):
    """read config from path or list of paths

    :param str|list[str] paths: path or list of paths
    :return dict: loaded and merged config
    """

    if isinstance(paths, str):
        paths = [paths]

    re = {}
    for path in paths:
        cfg = yaml.load(open(path))
        merge(re, cfg)

    return re


def merge(re, cfg):
    for category, category_data in cfg.items():
        if isinstance(category_data, dict):
            re.setdefault(category, {})
            for key, value in category_data.items():
                re[category][key] = value
        else:
            raise AttributeError(
                'Config files must be in format {category: {key: value, ...}, ...}')


def get_config_paths(module_name):
    cfg_name = module_name + '.yml'
    paths = []
    if module_name != 'rw':
        paths = get_config_paths('rw')
    paths += [
        pkg_resources.resource_filename(module_name, cfg_name),
        '/etc/' + cfg_name,
        os.path.expanduser('~/.') + cfg_name
    ]
    if 'VIRTUAL_ENV' in os.environ:
        paths.append(os.environ['VIRTUAL_ENV'] + '/etc/' + cfg_name)
    return paths


def read_configs(module_name, extra_configs=None):
    cfg = {}
    paths = get_config_paths(module_name)
    if extra_configs:
        if isinstance(extra_configs, list):
            paths.extend(extra_configs)
        else:
            paths.append(extra_configs)

    for path in paths:
        if os.path.exists(path):
            LOG.info('reading config: ' + path)
            tornado.autoreload.watch(path)
            merge(cfg, read_file(path))
    return cfg
