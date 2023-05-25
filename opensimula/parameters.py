import sys
from opensimula.Child import Child

# ___________________ Parameter _________________________


class Parameter(Child):
    """Elements with key-value pair"""

    def __init__(self, key, value=0):
        Child.__init__(self)
        self._key_ = key
        self._value_ = value

    @property
    def key(self):
        return self._key_

    @key.setter
    def key(self, key):
        self._key_ = key

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        self._value_ = value

    def info(self):
        return self.key + ": " + str(self.value)

    def check(self):
        return 0


# _____________ Parameter_boolean ___________________________


class Parameter_boolean(Parameter):
    def __init__(self, key, value=False):
        Parameter.__init__(self, key, value)

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        if isinstance(value, bool):
            self._value_ = value
        else:
            print("Error: ", value, " is not boolean, ", self.info())


class Parameter_boolean_list(Parameter):
    def __init__(self, key, value=[False]):
        Parameter.__init__(self, key, value)

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        error = False
        if not isinstance(value, list):
            error = True
        if not all(isinstance(n, bool) for n in value):
            error = True
        if error:
            print("Error: ", value, " is not a list of booleans, ", self.info())
        else:
            self._value_ = value


# _____________ Parameter_string ___________________________


class Parameter_string(Parameter):
    def __init__(self, key, value=""):
        Parameter.__init__(self, key, value)

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        self._value_ = str(value)


class Parameter_string_list(Parameter):
    def __init__(self, key, value=[""]):
        Parameter.__init__(self, key, value)

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        if not isinstance(value, list):
            self._value_ = [str(value)]
        else:
            for el in value:
                el = str(el)
            self._value_ = value


# _____________ Parameter_int ___________________________


class Parameter_int(Parameter):
    def __init__(self, key, value=0, unit="", min=0, max=sys.maxsize):
        Parameter.__init__(self, key, value)
        self._unit_ = unit
        self._min_ = min
        self._max_ = max

    @property
    def unit(self):
        return self._unit_

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        if isinstance(value, (int)):
            self._value_ = value
        else:
            print("Error: ", value, " is not integer, ", self.info())

    def info(self):
        return self.key + ": " + str(self.value) + " [" + self._unit_ + "]"

    def check(self):
        if self.value < self._min_ and self.value > self._max_:
            print(
                "Error: ", self.value, " is not at [", self._min_, ",", self._max_, "]"
            )
            return 1
        else:
            return 0


class Parameter_int_list(Parameter):
    def __init__(self, key, value=[0], unit="", min=0, max=sys.maxsize):
        Parameter.__init__(self, key, value)
        self._unit_ = unit
        self._min_ = min
        self._max_ = max

    @property
    def unit(self):
        return self._unit_

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        error = False
        if not isinstance(value, list):
            error = True
        if not all(isinstance(n, int) for n in value):
            error = True
        if error:
            print("Error: ", value, " is not a list of integers, ", self.info())
        else:
            self._value_ = value

    def check(self):
        nErrors = 0
        for n in self.value:
            if n < self._min_ or n > self._max_:
                print("Error: ", n, " is not at [", self._min_, ",", self._max_, "]")
                nErrors += 1
        return nErrors

    def info(self):
        return self.key + ": " + str(self.value) + " [" + self._unit_ + "]"


# _____________ Parameter_float ___________________________


class Parameter_float(Parameter_int):
    def __init__(self, key, value=0.0, unit="", min=0.0, max=float("inf")):
        Parameter_int.__init__(self, key, float(value), unit, float(min), float(max))

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        try:
            self._value_ = float(value)
        except ValueError:
            print("Error: ", ValueError, ", ", self.info())

    def check(self):
        if self.value < self._min_ and self.value > self._max_:
            print(
                "Error: ", self.value, " is not at [", self._min_, ",", self._max_, "]"
            )
            return 1
        else:
            return 0


class Parameter_float_list(Parameter_int_list):
    def __init__(self, key, value=[0.0], unit="", min=0.0, max=float("inf")):
        Parameter_int_list.__init__(self, key, value, unit, float(min), float(max))

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        try:
            if not isinstance(value, list):
                flotante = [float(value)]
            else:
                flotante = []
                for n in value:
                    flotante.append(float(n))
            self._value_ = flotante
        except ValueError:
            print("Error: ", ValueError, ", ", self.info())

    def check(self):
        nErrors = 0
        for n in self.value:
            if n < self._min_ or n > self._max_:
                print("Error: ", n, " is not at [", self._min_, ",", self._max_, "]")
                nErrors += 1
        return nErrors


# _____________ Parameter_options ___________________________


class Parameter_options(Parameter):
    def __init__(self, key, value="", options=[]):
        Parameter.__init__(self, key, value)
        self._options_ = options
        self.value = value  # To check included in options

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        self._value_ = str(value)

    @property
    def options(self):
        return self._options_

    def check(self):
        if self.value not in self.options:
            print("Error: ", self.value, " is not in options.")
            return 1
        else:
            return 0


class Parameter_options_list(Parameter):
    def __init__(self, key, value=[""], options=[]):
        Parameter.__init__(self, key, value)
        self._options_ = options
        self.value = value  # To check included in options

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        if not isinstance(value, list):
            self._value_ = [str(value)]
        else:
            for el in value:
                el = str(el)
            self._value_ = value

    @property
    def options(self):
        return self._options_

    def check(self):
        nErrors = 0
        for el in self.value:
            if el not in self.options:
                print("Error: ", el, " is not in options.")
                nErrors += 1
        return nErrors


# _____________ Parameter_component ___________________________


class Parameter_component(Parameter_string):
    def __init__(self, key, value=""):
        Parameter_string.__init__(self, key, value)

    def find_component(self):
        if "->" not in self.value:  # en el propio proyecto
            return self.parent.project.find_component(self.value)
        else:
            splits = self.value.split("->")
            proj = self.parent.simulation.find_project(splits[0])
            if proj == None:
                return None
            else:
                return proj.find_component(splits[1])

    def check(self):
        comp = self.find_component()
        if comp == None and self.value != "not_defined":
            print("Error: ", self.value, " component not found.")
            return 1
        else:
            return 0


class Parameter_component_list(Parameter_string_list):
    def __init__(self, key, value=[""]):
        Parameter_string.__init__(self, key, value)

    def find_component(self):
        components = []
        for element in self.value:
            if "->" not in element:  # en el propio proyecto
                components.append(self.parent.project.find_component(element))
            else:
                splits = element.split("->")
                proj = self.parent.simulation.find_project(splits[0])
                if proj == None:
                    components.append(None)
                else:
                    components.append(proj.find_component(splits[1]))
        return components

    def check(self):
        nErrors = 0
        comps = self.find_component()
        for i in range(len(comps)):
            if comps[i] == None and self.value[i] != "not_defined":
                print("Error: ", self.value[i], " component not found.")
                nErrors += 1
        return nErrors
