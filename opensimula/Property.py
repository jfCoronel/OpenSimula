from opensimula.Child import Child


class Property(Child):
    def __init__(self, name, value=0):
        Child.__init__(self)
        self._name = name
        self._value = value

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
