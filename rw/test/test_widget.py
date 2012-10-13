import rw


def test_widget():
    app = rw.load('rw.test.simple_app')
    assert 'example' in app.www.Main.widgets
