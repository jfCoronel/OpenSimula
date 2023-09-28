import sys
from OpenSimula.Child import Child

# ___________________ Parameter _________________________


class Parameter(Child):
    """Elements with key-value pair

    - key
    - value
    """

    def __init__(self, key, value=0):
        Child.__init__(self)
        self._key_ = key
        self._value_ = value
        self._sim_ = None

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

    @property
    def type(self):
        return type(self).__name__

    def info(self):
        return self.key + ": " + str(self.value)

    def check(self):
        return []


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
            self._sim_.print("Error: " + str(value) + " is not boolean, " + self.info())


class Parameter_boolean_list(Parameter):
    def __init__(self, key, value=[False]):
        Parameter.__init__(self, key, value)

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        try:
            if not isinstance(value, list):
                booleans = [bool(value)]
            else:
                booleans = []
                for n in value:
                    booleans.append(bool(n))
                self._value_ = booleans
        except ValueError as error:
            self._sim_.print("Error: " + str(error) + ", " + self.info())


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
            self._sim_.print("Error: " + str(value) + " is not integer, " + self.info())

    def info(self):
        return self.key + ": " + str(self.value) + " [" + self._unit_ + "]"

    def check(self):
        if self.value < self._min_ and self.value > self._max_:
            return [f"Error: {self.value} is not at [{self._min_},{self._max_}]"]
        else:
            return []


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
        try:
            if not isinstance(value, list):
                integers = [int(value)]
            else:
                integers = []
                for n in value:
                    integers.append(int(n))
                self._value_ = integers
        except ValueError as error:
            self._sim_.print("Error: " + str(error) + ", " + self.info())

    def check(self):
        errors = []
        for n in self.value:
            if n < self._min_ or n > self._max_:
                errors.append(f"Error: {n} is not at [{self._min_},{self._max_}]")
        return errors

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
        except ValueError as error:
            self._sim_.print("Error: " + str(error) + ", ", self.info())

    def check(self):
        if self.value < self._min_ and self.value > self._max_:
            return [f"Error: {self.value} is not at [{self._min_},{self._max_}]"]
        else:
            return []


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
        except ValueError as error:
            self._sim_.print("Error: " + str(error) + ", " + self.info())

    def check(self):
        errors = []
        for n in self.value:
            if n < self._min_ or n > self._max_:
                errors.append(f"Error: {n} is not at [{self._min_},{self._max_}]")
        return errors


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
            return [f"Error: {self.value} is not in options."]
        else:
            return []


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
        errors = []
        for el in self.value:
            if el not in self.options:
                errors.append(f"Error: {el} is not in options.")
        return errors


# _____________ Parameter_component ___________________________


class Parameter_component(Parameter):
    def __init__(self, key, value="not_defined", allowed_types=[]):
        Parameter.__init__(self, key, value)
        self.value = value
        self._allowed_types_ = allowed_types

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        self._value_ = str(value)
        if "->" in self.value:
            self._external_ = True
        else:
            self._external_ = False

    @property
    def external(self):
        return self._external_

    @property
    def allowed_types(self):
        return self._allowed_types_

    @property
    def component(self):
        if self.external:
            splits = self.value.split("->")
            proj = self.parent.project().simulation().project(splits[0])
            if proj == None:
                return None
            else:
                return proj.component(splits[1])
        else:
            return self.parent.project().component(self.value)

    def check(self):
        errors = []
        comp = self.component
        if len(self.allowed_types) > 0 and self.value != "not_defined":
            if type(comp).__name__ not in self.allowed_types:
                errors.append(
                    f"Error: {self.value} component is not one of the allowed types."
                )
        if comp == None and self.value != "not_defined":
            errors.append(f"Error: {self.value} component not found.")
        return errors


class Parameter_component_list(Parameter):
    def __init__(self, key, value=["not_defined"], allowed_types=[]):
        Parameter.__init__(self, key, value)
        self.value = value
        self._allowed_types_ = allowed_types

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
        self._external_ = []
        for el in self.value:
            if "->" in el:
                self._external_.append(True)
            else:
                self._external_.append(False)

    @property
    def external(self):
        return self._external_

    @property
    def allowed_types(self):
        return self._allowed_types_

    @property
    def component(self):
        components = []
        for i, element in enumerate(self.value):
            if self.external[i]:
                splits = element.split("->")
                proj = self.parent.project().simulation().project(splits[0])
                if proj == None:
                    components.append(None)
                else:
                    components.append(proj.component(splits[1]))
            else:
                components.append(self.parent.project().component(element))
        return components

    def check(self):
        errors = []
        comps = self.component
        for i in range(len(comps)):
            if len(self.allowed_types) > 0 and self.value[i] != "not_defined":
                if type(comps[i]).__name__ not in self.allowed_types:
                    errors.append(
                        f"Error: {self.value[i]} component is not one of the allowed types."
                    )
            if comps[i] == None and self.value[i] != "not_defined":
                errors.append(f"Error: {self.value[i]} component not found.")
        return errors
