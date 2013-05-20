import rbusys


class RequestHandling(rbusys.MultiPlug):
    def pre_process(self, handler):
        """pre processing for the RequestHandler.

        This must return a Future.
        """
        pass
