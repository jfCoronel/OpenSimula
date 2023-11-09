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
    
    def _get_error_header_ (self):
        return f'Error: {self.parent.parameter("name").value}->{self.key}. '


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
            msg = self._get_error_header_()+f"{str(value)} is not boolean."
            self._sim_.print(msg)


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
            msg = self._get_error_header_()+f"{str(error)}"
            self._sim_.print(msg)


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
            msg = self._get_error_header_()+f"{str(value)} is not integer."
            self._sim_.print(msg)

    def info(self):
        return self.key + ": " + str(self.value) + " [" + self._unit_ + "]"

    def check(self):
        if self.value < self._min_ or self.value > self._max_:
            msg = self._get_error_header_()+f"{self.value} is not at [{self._min_},{self._max_}]"
            return [msg]
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
            msg = self._get_error_header_()+f"{str(error)}"
            self._sim_.print(msg)

    def check(self):
        errors = []
        for n in self.value:
            if n < self._min_ or n > self._max_:
                msg = self._get_error_header_()+f"{n} is not at [{self._min_},{self._max_}]"
                errors.append(msg)
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
            msg = self._get_error_header_()+f"{str(error)}"
            self._sim_.print(msg)

    def check(self):
        if self.value < self._min_ or self.value > self._max_:
            msg = self._get_error_header_()+f"{self.value} is not at [{self._min_},{self._max_}]"
            return [msg]
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
            msg = self._get_error_header_()+f"{str(error)}"
            self._sim_.print(msg)

    def check(self):
        errors = []
        for n in self.value:
            if n < self._min_ or n > self._max_:
                msg = self._get_error_header_()+f"{n} is not at [{self._min_},{self._max_}]"
                errors.append(msg)
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
            msg = self._get_error_header_()+f"{self.value} is not in options."
            return [msg]
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
                msg = self._get_error_header_()+f"{el} is not in options."
                errors.append(msg)
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
                msg = self._get_error_header_()+f"{self.value} component is not of one of the allowed types."
                errors.append(msg)
        if comp == None and self.value != "not_defined":
            msg = self._get_error_header_() + f"{self.value} component not found."
            errors.append(msg)
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
                    msg = self._get_error_header_()+f"{self.value[i]} component is not of one of the allowed types."
                    errors.append(msg)
            if comps[i] == None and self.value[i] != "not_defined":
                msg = self._get_error_header_() + f"{self.value[i]} component not found."
                errors.append(msg)
        return errors


# _____________ Parameter_variable ___________________________


class Parameter_variable(Parameter):
    def __init__(self, key, value="not_defined = component.variable"):
        Parameter.__init__(self, key, value)
        self.value = value

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        format_error = False 
        self._value_ = str(value)
        if "=" in self._value_:
            splits = self._value_.split("=")
            self._symbol_ = splits[0].strip()
            if "." in splits[1]:
                splits2 =splits[1].split(".")
                self._component_ = splits2[0].strip()
                self._variable_ = splits2[1].strip()
            else: 
                format_error = True
        else:
            format_error = True

        if "->" in self._component_:
            self._external_ = True
        else:
            self._external_ = False
        
        if format_error:    
            msg = self._get_error_header_()+'Incorrect format. Expected format "symbol = component.variable"'
            self._sim_.print(msg)

    @property
    def external(self):
        return self._external_
    
    @property
    def symbol(self):
        return self._symbol_

    @property
    def variable(self):
        try:
            if self.external:
                splits = self._component_.split("->")
                proj = self.parent.project().simulation().project(splits[0].strip())
                var = proj.component(splits[1].strip()).variable(self._variable_)
            else:
                var = self.parent.project().component(self._component_).variable(self._variable_)
        except Exception as error:
            var = None
        
        return var

    def check(self):
        errors = []
        var = self.variable
        if var == None and self._symbol_ != "not_defined":
            msg = self._get_error_header_() + f"{self.value} component or variable not found."
            errors.append(msg)
        return errors


class Parameter_variable_list(Parameter):
    def __init__(self, key, value=["not_defined = component.variable"]):
        Parameter.__init__(self, key, value)
        self.value = value

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
        
        format_error = False 
        self._symbol_ = []
        self._component_ = []
        self._variable_ = []
        self._external_ = []
        for element in self._value_:
            if "=" in element:
                splits =element.split("=")
                self._symbol_.append(splits[0].strip())
                if "." in splits[1]:
                    splits2 =splits[1].split(".")
                    self._component_.append(splits2[0].strip())
                    self._variable_.append(splits2[1].strip())
                else: 
                    format_error = True
            else:
                format_error = True
            if "->" in element:
                self._external_.append(True)
            else:
                self._external_.append(False)

        if format_error:    
            msg = self._get_error_header_()+'Incorrect format. Expected format "symbol = component.variable"'
            self._sim_.print(msg)

    @property
    def external(self):
        return self._external_

    @property
    def symbol(self):
        return self._symbol_

    @property
    def variable(self):
        variables = []
        for i in range(len(self._value_)):
            try:
                if self.external[i]:
                    splits = self._component_[i].split("->")
                    proj = self.parent.project().simulation().project(splits[0].strip())
                    variables.append(proj.component(splits[1].strip()).variable(self._variable_[i]))
                else:
                    variables.append(self.parent.project().component(self._component_[i]).variable(self._variable_[i]))
            except Exception as error:
                variables.append(None)

        return variables

    def check(self):
        errors = []
        for i in range(len(self._value_)):
            var = self.variable[i]
            if var == None and self.symbol[i] != "not_defined":
                msg = self._get_error_header_() + f"{self.value} component or variable not found."
                errors.append(msg)
        return errors
