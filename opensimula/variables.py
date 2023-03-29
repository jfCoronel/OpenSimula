from .base import Child


class Variable(Child):
    def __init__(self, name):
        Child.__init__(self)
        self._name = name

    @property
    def name(self):
        return self._name
