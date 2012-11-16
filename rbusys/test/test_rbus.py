import pytest

import rbusys
rbusys.setup()
import rbus
import rplug


class EMailInterface(rbusys.SinglePlug):
    rbus_path = 'rw.email'

    def send(self):
        """Documentation Foo"""
        pass


class UnusedInterfaceSingle(rbusys.SinglePlug):
    rbus_path = 'rw.unused_s'

    def send(self):
        """Documentation Foo"""
        pass


class UnusedInterfaceMulti(rbusys.MultiPlug):
    rbus_path = 'rw.unused_m'

    def send(self):
        """Documentation Foo"""
        pass


class EMail(rplug.rw.email):
    def __init__(self):
        self.message_send = False

    def send(self):
        self.message_send = True

EMail.activate()


class LoggingInterface(rbusys.MultiPlug):
    rbus_path = 'rw.logging'

    def log(self, msg):
        pass


class Log0(rplug.rw.logging):
    def log(self, msg):
        Log0.last_msg = msg
        return 0


class Log1(rplug.rw.logging):
    def log(self, msg):
        Log1.last_msg = msg
        return 1


Log0.activate()
Log1.activate()


def test_singleton():
    assert not rbus.rw.email.message_send
    rbus.rw.email.send()
    assert rbus.rw.email.message_send


def test_multi():
    ret = rbus.rw.logging.log('a')
    assert 0 in ret
    assert 1 in ret
    assert len(ret) == 2
    assert Log0.last_msg == 'a'
    assert Log1.last_msg == 'a'

    ret = rbus.rw.logging.log('b')
    assert Log0.last_msg == 'b'
    assert Log1.last_msg == 'b'


class LoggingInterface2(rbusys.MultiPlug):
    rbus_path = 'rw.logging2'

    @rbusys.post_process
    def log(self, msg, _results=None):
        return sum(_results)


class Log0_2(rplug.rw.logging2):
    num = 0

    def log(self, msg):
        Log0_2.last_msg = msg
        return self.num


class Log1_2(rplug.rw.logging2):
    num = 1

    def log(self, msg):
        Log1_2.last_msg = msg
        return self.num


Log0_2.activate()
Log1_2.activate()


def test_post_processing_with_interface():
    assert rbus.rw.logging2.log('a') == 1
    assert Log0_2.last_msg == 'a'
    assert Log1_2.last_msg == 'a'

    Log0_2.num = 3
    assert rbus.rw.logging2.log('b') == 4
    assert Log0_2.last_msg == 'b'
    assert Log1_2.last_msg == 'b'


def test_nondefined():
    with pytest.raises(AttributeError):
        print rbus.rw.foo
    with pytest.raises(AttributeError):
        print rbus.foo.bar


def test_unused_interface():
    with pytest.raises(AttributeError):
        rbus.rw.unused_s.send()
    assert rbus.rw.unused_m.send() == []
    assert rbus.rw.unused_m.send.__doc__ != ""
    with pytest.raises(AttributeError):
        rbus.rw.unused_m.something_that_does_not_exist_in_interface()
