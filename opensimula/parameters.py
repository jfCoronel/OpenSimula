from opensimula.core import Parameter, Component


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
            self.parent.message(
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
                self.parent.message(
                    "Error: " + str(value) +
                    " is not at [" + str(self._min)+"," +
                    str(self._max) + "], "
                    + self.info())
        else:
            self.parent.message(
                "Error: " + str(value) +
                " is not number, " + self.info())

    def info(self):
        return self.name + ": " + str(self.value) + " ["+self._unit+"]"


class Parameter_component(Parameter):
    def __init__(self, name, value=""):
        Parameter.__init__(self, name, value)
        self._component = None

    @property
    def component(self):
        return self._component

    # @component.setter
    # def component(self, comp):
    #     if (isinstance(comp, (int, Component)) or comp == None):
    #         self._value = comp.name
    #     else:
    #         self.parent.message(
    #             "Error: " + str(comp) +
    #             " is not a Component")

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = str(value)
        self._findComponent()

    def info(self):
        if (self.component == None):
            return self.name + ": " + str(self.value) + " (Component not found)"
        else:
            return self.name + ": " + str(self.value)

    def _findComponent(self):
        if ("->" not in self.value):  # en el propio proyecto
            comp = self.parent.parent.find_component(self.value)
            self._component = comp
        # else:
