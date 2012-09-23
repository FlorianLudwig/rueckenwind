import rbusys


class IoloopException(rbusys.MultiPlug):
    def on_exception(self, e):
        """trigger when exception was raised

        e - Exception instance
        """
        pass
