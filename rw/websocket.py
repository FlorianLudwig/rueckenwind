import tornado.websocket


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        tornado.websocket.WebSocketHandler.__init__(self, application, request,
                                                                      **kwargs)
        # cleanup unused tornado features to avoid memory leak
        self.ui.clear()
