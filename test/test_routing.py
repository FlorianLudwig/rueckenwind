import pytest
import tornado.testing

import rw.routing
import rw.scope


def generate_rule(route):
    return rw.routing.Rule(route)


def test_parse_rule():
    assert rw.routing.parse_rule('/asdf/') == [(None, None, '/asdf/')]
    rule = rw.routing.parse_rule('/foo/<name>/bar')
    assert rule[0] == (None, None, '/foo/')
    assert rule[1] == ('str', None, 'name')
    assert rule[2] == (None, None, '/bar')


def test_parse_rule_errors():
    with pytest.raises(ValueError):
        # the argument name "name" is used twice
        list(rw.routing.parse_rule('/<name>/<name>/asd'))

    with pytest.raises(ValueError):
        # missing > after name
        list(rw.routing.parse_rule('/<name/asd'))


def test_rule_compare():
    for rule_0, rule_1 in (
        (generate_rule('/name'), generate_rule('/<something>')),
        (generate_rule('/name'), generate_rule('/na<something>')),
        (generate_rule('/name<something>'), generate_rule('/na<something>')),
        (generate_rule('/<something:int>'), generate_rule('/<something>')),
    ):
        assert rule_0 < rule_1
        assert rule_1 > rule_0

    assert not generate_rule('/name') < generate_rule('/name')
    assert not generate_rule('/name') > generate_rule('/name')


def test_rule_eq():
    assert generate_rule('/') == generate_rule('/')
    assert generate_rule('/foo') == generate_rule('/foo')
    assert generate_rule('/name/<name>/photo') == generate_rule('/name/<name>/photo')
    assert generate_rule('/name/<name>/photo/<num:int>') == generate_rule('/name/<name>/photo/<num:int>')

    assert generate_rule('/') != generate_rule('/foo')
    assert generate_rule('/name/<name>/photo/<num>') != generate_rule('/name/<name>/photo/<num:int>')


def test_rule_sorting():
    rules = [
        generate_rule('/name'),
        generate_rule('/'),
        generate_rule('/name/<name>/photo'),
        generate_rule('/name/<else>'),
        generate_rule('/<something>'),
    ]
    rules2 = rules[:]
    rules2.sort()
    assert rules == rules2

    rules3 = rules[:]
    rules3.reverse()
    rules3.sort()
    assert rules == rules3


def test_reverse_path():
    assert generate_rule('/').get_path() == '/'
    assert generate_rule('/somewhere').get_path() == '/somewhere'
    assert generate_rule('/user/<user>').get_path({'user': 'dino'}) == '/user/dino'


def test_converter_default():
    assert (3, 'foo') == rw.routing.converter_default('foo')
    assert (3, 'foo') == rw.routing.converter_default('foo/bar')


def test_convert_int():
    assert rw.routing.converter_int('123') == (3, 123)
    assert rw.routing.converter_int('4321Hello World') == (4, 4321)
    assert rw.routing.converter_int('-1431') == (5, -1431)
    with pytest.raises(rw.routing.NoMatchError):
        rw.routing.converter_int('foo')


def test_convert_uint():
    assert rw.routing.converter_uint('123') == (3, 123)
    assert rw.routing.converter_uint('4321Hello World') == (4, 4321)

    with pytest.raises(rw.routing.NoMatchError):
        assert rw.routing.converter_uint('-1431') == (5, -1431)


class MyTestCase(tornado.testing.AsyncTestCase):
    def test_rule_match(self):
        # match must be used inside scope with rw.routing:plugin activated
        scope = rw.scope.Scope()

        with scope():
            scope.activate(rw.routing.plugin, callback=self.inside_scope)

    def inside_scope(self, result):
        assert generate_rule('/').match('/') == {}
        assert generate_rule('/').match('/asd') is None
        assert generate_rule('/<foo>').match('/asd') == {'foo': 'asd'}
