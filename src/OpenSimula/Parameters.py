import sys
from py_expression_eval import Parser
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

    def _get_error_header_(self):
        return f'Error: {self.parent.parameter("name").value}->{self.key}. '

    def _cast_to_bool_(self, input_value):
        if isinstance(input_value, bool):
            return (input_value, 'ok')
        elif isinstance(input_value, str):
            if (input_value == 'True'):
                return (True, 'ok')
            elif (input_value == 'False'):
                return (False, 'ok')
            else:
                return (True, f"{input_value} cannot be converted to boolean.")
        else:
            return (True, f"{str(input_value)} is not boolean.")

    def _cast_to_int_(self, input_value):
        if isinstance(input_value, int):
            return (input_value, 'ok')
        elif isinstance(input_value, str):
            try:
                number = int(input_value)
                return (number, 'ok')
            except ValueError:
                return (0, f"{input_value} cannot be converted to int.")
        else:
            return (0, f"{str(input_value)} is not int.")

    def _cast_to_float_(self, input_value):
        if isinstance(input_value, float):
            return (input_value, 'ok')
        elif isinstance(input_value, int):
            return (float(input_value), 'ok')
        elif isinstance(input_value, str):
            try:
                number = float(input_value)
                return (number, 'ok')
            except ValueError:
                return (0.0, f"{input_value} cannot be converted to float.")
        else:
            return (0.0, f"{str(input_value)} is not float.")

    def _cast_to_string_list_(self, input_strig):
        if isinstance(input_strig, str):
            line = input_strig.strip()
            if line[0] == "[" and line[-1] == "]":
                stripped = [s.strip() for s in line[1:-1].split(',')]
                return (stripped, 'ok')
            else:
                return ([], f"{str(input_strig)} do not start with '[' or finish with ']'.")
        else:
            return ([], f"{str(input_strig)} is not string.")


# _____________ Parameter_boolean ___________________________


class Parameter_boolean(Parameter):
    def __init__(self, key, value=False):
        Parameter.__init__(self, key, value)

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        val, msg = self._cast_to_bool_(value)
        if (msg == 'ok'):
            self._value_ = val
        else:
            self._sim_.print(self._get_error_header_()+msg)


class Parameter_boolean_list(Parameter):
    def __init__(self, key, value=[False]):
        Parameter.__init__(self, key, value)

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        if not isinstance(value, list):
            val, msg = self._cast_to_string_list_(value)
            if (msg == 'ok'):
                value = val
            else:
                self._sim_.print(self._get_error_header_()+msg)
                return
        # Is a list
        final_values = []
        for n in value:
            val, msg = self._cast_to_bool_(n)
            final_values.append(val)
            if (msg != 'ok'):
                self._sim_.print(self._get_error_header_()+msg)
        self._value_ = final_values


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
            val, msg = self._cast_to_string_list_(value)
            if (msg == 'ok'):
                self._value_ = val
            else:
                self._sim_.print(self._get_error_header_()+msg)
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
        val, msg = self._cast_to_int_(value)
        if (msg == 'ok'):
            self._value_ = val
        else:
            self._sim_.print(self._get_error_header_()+msg)

    def info(self):
        return self.key + ": " + str(self.value) + " [" + self._unit_ + "]"

    def check(self):
        if self.value < self._min_ or self.value > self._max_:
            msg = self._get_error_header_(
            )+f"{self.value} is not at [{self._min_},{self._max_}]"
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
        if not isinstance(value, list):
            val, msg = self._cast_to_string_list_(value)
            if (msg == 'ok'):
                value = val
            else:
                self._sim_.print(self._get_error_header_()+msg)
                return
        # Is a list
        final_values = []
        for n in value:
            val, msg = self._cast_to_int_(n)
            final_values.append(val)
            if (msg != 'ok'):
                self._sim_.print(self._get_error_header_()+msg)
        self._value_ = final_values

    def check(self):
        errors = []
        for n in self.value:
            if n < self._min_ or n > self._max_:
                msg = self._get_error_header_(
                )+f"{n} is not at [{self._min_},{self._max_}]"
                errors.append(msg)
        return errors

    def info(self):
        return self.key + ": " + str(self.value) + " [" + self._unit_ + "]"


# _____________ Parameter_float ___________________________


class Parameter_float(Parameter_int):
    def __init__(self, key, value=0.0, unit="", min=0.0, max=float("inf")):
        Parameter_int.__init__(self, key, float(
            value), unit, float(min), float(max))

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        val, msg = self._cast_to_float_(value)
        if (msg == 'ok'):
            self._value_ = val
        else:
            self._sim_.print(self._get_error_header_()+msg)

    def check(self):
        if self.value < self._min_ or self.value > self._max_:
            msg = self._get_error_header_(
            )+f"{self.value} is not at [{self._min_},{self._max_}]"
            return [msg]
        else:
            return []


class Parameter_float_list(Parameter_int_list):
    def __init__(self, key, value=[0.0], unit="", min=0.0, max=float("inf")):
        Parameter_int_list.__init__(
            self, key, value, unit, float(min), float(max))

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        if not isinstance(value, list):
            val, msg = self._cast_to_string_list_(value)
            if (msg == 'ok'):
                value = val
            else:
                self._sim_.print(self._get_error_header_()+msg)
                return
        # Is a list
        final_values = []
        for n in value:
            val, msg = self._cast_to_float_(n)
            final_values.append(val)
            if (msg != 'ok'):
                self._sim_.print(self._get_error_header_()+msg)
        self._value_ = final_values

    def check(self):
        errors = []
        for n in self.value:
            if n < self._min_ or n > self._max_:
                msg = self._get_error_header_(
                )+f"{n} is not at [{self._min_},{self._max_}]"
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
            val, msg = self._cast_to_string_list_(value)
            if (msg == 'ok'):
                self._value_ = val
            else:
                self._sim_.print(self._get_error_header_()+msg)
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
            proj = self.parent.project()._sim_.project(splits[0])
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
                msg = self._get_error_header_(
                )+f"{self.value} component is not of one of the allowed types."
                errors.append(msg)
        if comp == None and self.value != "not_defined":
            msg = self._get_error_header_(
            ) + f"{self.value} component not found."
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
            val, msg = self._cast_to_string_list_(value)
            value = val
            if (msg != 'ok'):
                self._sim_.print(self._get_error_header_()+msg)
                return
        # Is a list
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
                proj = self.parent.project()._sim_.project(splits[0])
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
                    msg = self._get_error_header_(
                    )+f"{self.value[i]} component is not of one of the allowed types."
                    errors.append(msg)
            if comps[i] == None and self.value[i] != "not_defined":
                msg = self._get_error_header_(
                ) + f"{self.value[i]} component not found."
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
                splits2 = splits[1].split(".")
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
            msg = self._get_error_header_(
            )+'Incorrect format. Expected format "symbol = component.variable"'
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
                proj = self.parent.project()._sim_.project(
                    splits[0].strip())
                var = proj.component(
                    splits[1].strip()).variable(self._variable_)
            else:
                var = self.parent.project().component(self._component_).variable(self._variable_)
        except Exception as error:
            var = None

        return var

    def check(self):
        errors = []
        var = self.variable
        if var == None and self._symbol_ != "not_defined":
            msg = self._get_error_header_(
            ) + f"{self.value} component or variable not found."
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
            val, msg = self._cast_to_string_list_(value)
            value = val
            if (msg != 'ok'):
                self._sim_.print(self._get_error_header_()+msg)
                return
        # Is a list
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
                splits = element.split("=")
                self._symbol_.append(splits[0].strip())
                if "." in splits[1]:
                    splits2 = splits[1].split(".")
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
            msg = self._get_error_header_(
            )+'Incorrect format. Expected format "symbol = component.variable"'
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
                    proj = self.parent.project()._sim_.project(
                        splits[0].strip())
                    variables.append(proj.component(
                        splits[1].strip()).variable(self._variable_[i]))
                else:
                    variables.append(self.parent.project().component(
                        self._component_[i]).variable(self._variable_[i]))
            except Exception as error:
                variables.append(None)

        return variables

    def check(self):
        errors = []
        for i in range(len(self._value_)):
            var = self.variable[i]
            if var == None and self.symbol[i] != "not_defined":
                msg = self._get_error_header_(
                ) + f"{self.value} component or variable not found."
                errors.append(msg)
        return errors


# _____________ Parameter_math_exp ___________________________


class Parameter_math_exp(Parameter):
    def __init__(self, key, value="0.0", unit=""):
        Parameter.__init__(self, key, value)
        self._unit_ = unit
        self._parser_ = Parser()

    @property
    def unit(self):
        return self._unit_

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        self._value_ = str(value)

    def check(self):
        try:
            self._parser_.parse(self.value)
        except Exception as error:
            return [self._get_error_header_()+f"{str(error)}"]
        return []

    def evaluate(self, values_dic):
        return self._parser_.parse(self.value).evaluate(values_dic)


class Parameter_math_exp_list(Parameter):
    def __init__(self, key, value=["0.0"], unit=""):
        Parameter.__init__(self, key, value)
        self._unit_ = unit
        self._parser_ = Parser()

    @property
    def unit(self):
        return self._unit_

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        if not isinstance(value, list):
            val, msg = self._cast_to_string_list_(value)
            value = val
            if (msg != 'ok'):
                self._sim_.print(self._get_error_header_()+msg)
                return
        # Is a list
        for el in value:
            el = str(el)
        self._value_ = value

    def check(self):
        errors = []
        for n in self.value:
            try:
                self._parser_.parse(n)
            except Exception as error:
                errors.append(self._get_error_header_()+f"{str(error)}")
        return errors

    def evaluate(self, i, values_dic):
        return self._parser_.parse(self.value[i]).evaluate(values_dic)
