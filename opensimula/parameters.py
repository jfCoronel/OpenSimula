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


class Parameter_boolean_List(Parameter):
    def __init__(self, key, value=[False]):
        Parameter.__init__(self, key, value)

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        test_type = all(isinstance(n, bool) for n in value)
        if test_type:
            self._value_ = value
        else:
            print("Error: ", value, " is not a list of booleans, ", self.info())


# _____________ Parameter_string ___________________________


class Parameter_string(Parameter):
    def __init__(self, key, value=""):
        Parameter.__init__(self, key, value)

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        self._value_ = value


class Parameter_string_List(Parameter):
    def __init__(self, key, value=[""]):
        Parameter.__init__(self, key, value)

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        test_type = all(isinstance(n, str) for n in value)
        if test_type:
            self._value_ = value
        else:
            print("Error: ", value, " is not a a list of strings, ", self.info())


# _____________ Parameter_number ___________________________


class Parameter_number(Parameter):
    def __init__(self, key, value=0.0, unit="", min=0, max=float("inf")):
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
        if isinstance(value, (int, float)):
            if value >= self._min_ and value <= self._max_:
                self._value_ = value
            else:
                print(
                    "Error: ",
                    value,
                    " is not at [",
                    self._min_,
                    ",",
                    self._max_,
                    "], ",
                    self.info(),
                )
        else:
            print("Error: ", value, " is not number, ", self.info())

    def info(self):
        return self.key + ": " + str(self.value) + " [" + self._unit_ + "]"


class Parameter_number_List(Parameter):
    def __init__(self, key, value=[0.0], unit="", min=0, max=float("inf")):
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
        test_type = all(isinstance(n, (float, int)) for n in value)
        if test_type:
            self._value_ = value
        else:
            print("Error: ", value, " is not a a list of numbers, ", self.info())

        for n in value:
            if n < self._min_ or n > self._max_:
                print(
                    "Error: ",
                    n,
                    " is not at [",
                    self._min_,
                    ",",
                    self._max_,
                    "], ",
                    self.info(),
                )

    def info(self):
        return self.key + ": " + str(self.value) + " [" + self._unit_ + "]"


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
        if value in self.options:
            self._value_ = str(value)
        else:
            print("Error: ", value, " is not in options, ", self.info())

    @property
    def options(self):
        return self._options_


class Parameter_options_List(Parameter):
    def __init__(self, key, value=[""], options=[]):
        Parameter.__init__(self, key, value)
        self._options_ = options
        self.value = value  # To check included in options

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        test_type = all(isinstance(n, str) for n in value)
        if test_type:
            self._value_ = value
        else:
            print("Error: ", value, " is not a a list of strings, ", self.info())

        for n in value:
            if n not in self.options:
                print("Error: ", n, " is not in options, ", self.info())

    @property
    def options(self):
        return self._options_


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


class Parameter_component_List(Parameter_string_List):
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
