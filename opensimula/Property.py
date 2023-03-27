from opensimula.Child import Child


class Property(Child):
    def __init__(self, name, default_value=0, value=0):
        Child.__init__(self)
        self._name = name
        self._default_value = default_value
        self._value = value

    @property
    def name(self):
        return self._name

    @property
    def default_value(self):
        return self._default_value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
