import os
import rw.cfg

import pytest

BASE = os.path.dirname(__file__)


def test_merge():
    # check to merge two config files
    foo = {'c': {'foo': 1}}
    cfg = {}
    rw.cfg.merge(cfg, foo)
    assert cfg == foo

    rw.cfg.merge(cfg, {})
    assert cfg == foo

    # configs must be dict of dicts
    with pytest.raises(AttributeError):
        rw.cfg.merge({}, 1)

    with pytest.raises(AttributeError):
        rw.cfg.merge({}, {'a': 1})


def test_simple():
    cfg = rw.cfg.read_file(BASE + '/configs/simple.yml')
    assert isinstance(cfg, dict)
    assert cfg['rw.plugins']['rw.db'] is True

    cfg = rw.cfg.read_file([
        BASE + '/configs/simple.yml',
        BASE + '/configs/no_rwdb.yml'
    ])
    assert cfg['rw.plugins']['rw.db'] is False
    assert cfg['rw.plugins']['someother_db'] is True

    cfg = rw.cfg.read_file([
        BASE + '/configs/no_rwdb.yml',
        BASE + '/configs/simple.yml',
    ])
    assert cfg['rw.plugins']['rw.db'] is True
    assert cfg['rw.plugins']['someother_db'] is True