from opensimula.base import Child


class Parameter(Child):
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

    def info(self):
        return self.name + ": " + str(self.value)


class Parameter_boolean(Parameter):
    def __init__(self, name, value=False):
        Parameter.__init__(self, name, value)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if (isinstance(value, bool)):
            self._value = value
        else:
            self.parent.simulation.message(
                "Error: " + str(value) +
                " is not boolean, " + self.info())


class Parameter_string(Parameter):
    def __init__(self, name, value=""):
        Parameter.__init__(self, name, value)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = str(value)


class Parameter_number(Parameter):
    def __init__(self, name, value=0.0, unit="", min=0, max=float('inf')):
        Parameter.__init__(self, name, value)
        self._unit = unit
        self._min = min
        self._max = max

    @property
    def unit(self):
        return self._unit

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if (isinstance(value, (int, float))):
            if (value >= self._min and value <= self._max):
                self._value = value
            else:
                self.parent.simulation.message(
                    "Error: " + str(value) +
                    " is not at [" + str(self._min)+"," +
                    str(self._max) + "], "
                    + self.info())
        else:
            self.parent.simulation.message(
                "Error: " + str(value) +
                " is not number, " + self.info())

    def info(self):
        return self.name + ": " + str(self.value) + " ["+self._unit+"]"
