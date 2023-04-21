from opensimula.Child import Child

# ___________________ Parameter _________________________


class Parameter(Child):
    """Elements with key-value pair"""

    def __init__(self, key, value=0):
        Child.__init__(self)
        self._key = key
        self._value = value

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, key):
        self._key = key

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    def info(self):
        return self.key + ": " + str(self.value)

# _____________ Parameter_boolean ___________________________


class Parameter_boolean(Parameter):
    def __init__(self, key, value=False):
        Parameter.__init__(self, key, value)

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


# _____________ Parameter_string ___________________________


class Parameter_string(Parameter):
    def __init__(self, key, value=""):
        Parameter.__init__(self, key, value)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = str(value)


# _____________ Parameter_number ___________________________


class Parameter_number(Parameter):
    def __init__(self, key, value=0.0, unit="", min=0, max=float('inf')):
        Parameter.__init__(self, key, value)
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
        return self.key + ": " + str(self.value) + " ["+self._unit+"]"

# _____________ Parameter_options ___________________________


class Parameter_options(Parameter):
    def __init__(self, key, value="", options=[]):
        Parameter.__init__(self, key, value)
        self._options = options
        self.value = value  # To check included in options

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if (value in self.options):
            self._value = str(value)
        else:
            self.parent.message(
                "Error: " + str(value) +
                " is not in options, " + self.info())

    @property
    def options(self):
        return self._options


# _____________ Parameter_component ___________________________

class Parameter_component(Parameter):
    def __init__(self, key, value=""):
        Parameter.__init__(self, key, value)
        self._component = None

    @property
    def component(self):
        return self._component

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = str(value)
        # self._findComponent()  hacerlo cuando estén todos los componentes cargados en la función check del componente

    def info(self):
        if (self.component == None):
            return self.key + ": " + str(self.value) + " (Component not found)"
        else:
            return self.key + ": " + str(self.value)

    def findComponent(self):
        if ("->" not in self.value):  # en el propio proyecto
            comp = self.parent.parent.find_component(self.value)
            self._component = comp
        # else:
