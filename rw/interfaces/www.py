import rbusys


class WWW(rbusys.MultiPlug):
    rbus_path = 'rw.www'

    """Plugins must inherit from rw.RequestHandler

    No other special methods must be implemented.
    All handlers are served via /_rw/"""
