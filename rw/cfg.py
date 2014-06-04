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
import yaml


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
            raise AttributeError('Config files must be in format {category: {key: value, ...}, ...}')

