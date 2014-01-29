from rw.widget import Widget


class Example(Widget):
    def render(self):
        self.finish(template='example.html')
