import rw.db


class Something(rw.db.Document):
    value0 = rw.db.Field(int)
    value1 = rw.db.Field(unicode, default=u'Hello World')


def test_default_values():
    s = Something()
    # s must have 'value1' without .value beeing accessed beforehand
    assert s == {'value1': u'Hello World'}
    assert s['value1'] == u'Hello World'
