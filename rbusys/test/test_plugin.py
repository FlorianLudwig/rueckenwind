import rbusys
rbusys.setup()

from rw.plugins import mail_local
mail_local.activate()


def test_mail():
    import rbus.rw.email
    assert hasattr(rbus.rw.email, 'send')
