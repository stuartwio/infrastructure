class File(object):

    def __init__(self, path):
        self.path = path

    def read(self) -> str:
        with open(self.path, 'r') as f:
            return f.read()
