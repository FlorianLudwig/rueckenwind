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

