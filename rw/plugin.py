import rw.event
import rw.scope


class Plugin(object):
    def __init__(self, name):
        self.name = name
        self.activate = rw.event.Event()

    def init(self, function):
        function = rw.scope.inject(function)
        self.activate.add(function)
        return function