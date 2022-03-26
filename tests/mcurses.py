class MWindow:
    def __init__(self, width, height):
        self.x = width
        self.y = height

    def getmaxyx(self):
        return (self.y, self.x)

    def addstr(self, *args, **kwargs):
        pass

    def refresh(self):
        pass

    def resize(self, *args, **kwargs):
        pass

    def clear(self):
        pass

    def vline(self, *args, **kwargs):
        pass
