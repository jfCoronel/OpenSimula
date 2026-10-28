import sys
import math  #Needed for expressions
from opensimula.Child import Child
from opensimula.Message import Message

# ___________________ Parameter _________________________


class Parameter(Child):
    """Elements with key-value pair

    Base class of all the parameters. Each subclass converts the values it receives
    (also from strings, as read from Excel or a form) to its type in the `value` setter,
    reporting an error message if it cannot, and validates them in `check()`. The
    `_list` subclasses hold a list of values; a single value is accepted and stored as a
    one-element list.
    """

    def __init__(self, key, value=0):
        """Create new parameter

        Args:
            key (str): key of the parameter in its container
            value (optional): initial value. Defaults to 0.
        """
        Child.__init__(self)
        self._key_ = key
        self._value_ = value
        self._sim_ = None

    @property
    def key(self):
        """str: key of the parameter in its container"""
        return self._key_

    @key.setter
    def key(self, key):
        self._key_ = key

    @property
    def value(self):
        """Value of the parameter, converted to its type when set"""
        return self._value_

    @value.setter
    def value(self, value):
        self._value_ = value

    @property
    def type(self):
        """str: class name of the parameter, e.g. "Parameter_float" """
        return type(self).__name__

    def info(self):
        """Key and value as text

        Returns:
            str: "key: value", with the unit for numeric parameters
        """
        return self.key + ": " + str(self.value)

    def check(self):
        """Check if the value is correct

        Returns:
            list of Message: errors found
        """
        return []

    def _get_error_header_(self):
        return f'{self.parent.parameter("name").value}->{self.key}: '

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
    """Boolean parameter (also accepts the strings "True" and "False")"""

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
            self._sim_.message(Message(self._get_error_header_()+msg,"ERROR"))

class Parameter_boolean_list(Parameter):
    """List of booleans"""

    def __init__(self, key, value=[False]):
        Parameter.__init__(self, key, value)

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        if isinstance(value, bool): # Single boolean
            value = [value]
        if not isinstance(value, list):
            val, msg = self._cast_to_string_list_(value)
            if (msg == 'ok'):
                value = val
            else:
                self._sim_.message(Message(self._get_error_header_()+msg,"ERROR"))
                return
        # Is a list
        final_values = []
        for n in value:
            val, msg = self._cast_to_bool_(n)
            final_values.append(val)
            if (msg != 'ok'):
                self._sim_.message(Message(self._get_error_header_()+msg,"ERROR"))
        self._value_ = final_values


# _____________ Parameter_string ___________________________


class Parameter_string(Parameter):
    """String parameter"""

    def __init__(self, key, value=""):
        Parameter.__init__(self, key, value)

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        self._value_ = str(value)


class Parameter_string_list(Parameter):
    """List of strings (also accepts a string "[a, b, c]")"""

    def __init__(self, key, value=[""]):
        Parameter.__init__(self, key, value)

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        if isinstance(value, str): # Single string
            value = [value]
        if not isinstance(value, list):
            val, msg = self._cast_to_string_list_(value)
            if (msg == 'ok'):
                self._value_ = val
            else:
                self._sim_.message(Message(self._get_error_header_()+msg,"ERROR"))
        else:
            for el in value:
                el = str(el)
            # Own copy: keeping the caller list would let it be mutated from
            # outside, and would be shared by every parameter assigned from it
            self._value_ = list(value)


# _____________ Parameter_int ___________________________


class Parameter_int(Parameter):
    """Integer parameter with unit and allowed range

    Args:
        key (str): key of the parameter
        value (int, optional): initial value. Defaults to 0.
        unit (str, optional): unit. Defaults to "".
        min (int, optional): minimum value, checked by check(). Defaults to 0.
        max (int, optional): maximum value, checked by check(). Defaults to sys.maxsize.
    """

    def __init__(self, key, value=0, unit="", min=0, max=sys.maxsize):
        Parameter.__init__(self, key, value)
        self._unit_ = unit
        self._min_ = min
        self._max_ = max

    @property
    def unit(self):
        return self._unit_

    @property
    def min(self):
        return self._min_

    @property
    def max(self):
        return self._max_

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        val, msg = self._cast_to_int_(value)
        if (msg == 'ok'):
            self._value_ = val
        else:
            self._sim_.message(Message(self._get_error_header_()+msg,"ERROR"))

    def info(self):
        return self.key + ": " + str(self.value) + " [" + self._unit_ + "]"

    def check(self):
        if self.value < self._min_ or self.value > self._max_:
            msg = self._get_error_header_()+f"{self.value} is not at [{self._min_},{self._max_}]"
            return [Message(msg,"ERROR")]
        else:
            return []


class Parameter_int_list(Parameter):
    """List of integers with unit and allowed range (same arguments as Parameter_int)"""

    def __init__(self, key, value=[0], unit="", min=0, max=sys.maxsize):
        Parameter.__init__(self, key, value)
        self._unit_ = unit
        self._min_ = min
        self._max_ = max

    @property
    def unit(self):
        return self._unit_

    @property
    def min(self):
        return self._min_

    @property
    def max(self):
        return self._max_

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        if isinstance(value, int): # Single integer
            value = [value]
        if not isinstance(value, list):
            val, msg = self._cast_to_string_list_(value)
            if (msg == 'ok'):
                value = val
            else:
                self._sim_.message(Message(self._get_error_header_()+msg,"ERROR"))
                return
        # Is a list
        final_values = []
        for n in value:
            val, msg = self._cast_to_int_(n)
            final_values.append(val)
            if (msg != 'ok'):
                self._sim_.message(Message(self._get_error_header_()+msg,"ERROR"))
        self._value_ = final_values

    def check(self):
        errors = []
        for n in self.value:
            if n < self._min_ or n > self._max_:
                msg = self._get_error_header_()+f"{n} is not at [{self._min_},{self._max_}]"
                errors.append(Message(msg,"ERROR"))
        return errors

    def info(self):
        return self.key + ": " + str(self.value) + " [" + self._unit_ + "]"


# _____________ Parameter_float ___________________________


class Parameter_float(Parameter_int):
    """Float parameter with unit and allowed range

    Args:
        key (str): key of the parameter
        value (float, optional): initial value. Defaults to 0.0.
        unit (str, optional): unit, e.g. "W/m²". Defaults to "".
        min (float, optional): minimum value, checked by check(). Defaults to -inf.
        max (float, optional): maximum value, checked by check(). Defaults to inf.
    """

    def __init__(self, key, value=0.0, unit="", min=float("-inf"), max=float("inf")):
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
            self._sim_.message(Message(self._get_error_header_()+msg,"ERROR"))

    def check(self):
        if self.value < self._min_ or self.value > self._max_:
            msg = self._get_error_header_()+f"{self.value} is not at [{self._min_},{self._max_}]"
            return [Message(msg,"ERROR")]
        else:
            return []


class Parameter_float_list(Parameter_int_list):
    """List of floats with unit and allowed range (same arguments as Parameter_float)"""

    def __init__(self, key, value=[0.0], unit="", min=float("-inf"), max=float("inf")):
        Parameter_int_list.__init__(
            self, key, value, unit, float(min), float(max))

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        if isinstance(value, float): # Single float
            value = [value]
        if not isinstance(value, list):
            val, msg = self._cast_to_string_list_(value)
            if (msg == 'ok'):
                value = val
            else:
                self._sim_.message(Message(self._get_error_header_()+msg,"ERROR"))
                return
        # Is a list
        final_values = []
        for n in value:
            val, msg = self._cast_to_float_(n)
            final_values.append(val)
            if (msg != 'ok'):
                self._sim_.message(Message(self._get_error_header_()+msg,"ERROR"))
        self._value_ = final_values

    def check(self):
        errors = []
        for n in self.value:
            if n < self._min_ or n > self._max_:
                msg = self._get_error_header_()+f"{n} is not at [{self._min_},{self._max_}]"
                errors.append(Message(msg,"ERROR"))
        return errors


# _____________ Parameter_options ___________________________


class Parameter_options(Parameter):
    """String parameter that must be one of a list of options

    Args:
        key (str): key of the parameter
        value (str, optional): initial value. Defaults to "".
        options (list of str, optional): allowed values, checked by check(). Defaults to [].
    """

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
            return [Message(msg,"ERROR")]
        else:
            return []


class Parameter_options_list(Parameter):
    """List of strings, each one of a list of options"""

    def __init__(self, key, value=[""], options=[]):
        Parameter.__init__(self, key, value)
        self._options_ = options
        self.value = value  # To check included in options

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        if isinstance(value, str): # Single string
            value = [value]
        if not isinstance(value, list):
            val, msg = self._cast_to_string_list_(value)
            if (msg == 'ok'):
                self._value_ = val
            else:
                self._sim_.message(Message(self._get_error_header_()+msg,"ERROR"))
        else:
            for el in value:
                el = str(el)
            # Own copy: keeping the caller list would let it be mutated from
            # outside, and would be shared by every parameter assigned from it
            self._value_ = list(value)

    @property
    def options(self):
        return self._options_

    def check(self):
        errors = []
        for el in self.value:
            if el not in self.options:
                msg = self._get_error_header_()+f"{el} is not in options."
                errors.append(Message(msg,"ERROR"))
        return errors


# _____________ Parameter_component ___________________________


class Parameter_component(Parameter):
    """Reference to another component, by its name

    The value is the name of the component in the same project, or
    "project_name->component_name" for a component of another project of the simulation.
    "not_defined" means no reference.

    Args:
        key (str): key of the parameter
        value (str, optional): name of the component. Defaults to "not_defined".
        allowed_types (list of str, optional): component types allowed, checked by
            check(); empty allows any. Defaults to [].
    """

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
        """Component: referenced component, None if not found"""
        if self.external:
            splits = self.value.split("->")
            proj = self.parent.project()._sim_.project(splits[0])
            if proj is None:
                return None
            else:
                return proj.component(splits[1])
        else:
            if self.parent.__class__.__name__== "Project":
                return self.parent.component(self.value)
            else:
                return self.parent.project().component(self.value)

    def check(self):
        errors = []
        comp = self.component
        if len(self.allowed_types) > 0 and self.value != "not_defined":
            if type(comp).__name__ not in self.allowed_types:
                msg = self._get_error_header_()+f"{self.value} component is not of one of the allowed types."
                errors.append(Message(msg,"ERROR"))
        if comp is None and self.value != "not_defined":
            msg = self._get_error_header_() + f"{self.value} component not found."
            errors.append(Message(msg,"ERROR"))
        return errors


class Parameter_component_list(Parameter):
    """List of references to components (same format as Parameter_component)"""

    def __init__(self, key, value=["not_defined"], allowed_types=[]):
        Parameter.__init__(self, key, value)
        self.value = value
        self._allowed_types_ = allowed_types

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        if isinstance(value, str): # Single string
            value = [value]
        if not isinstance(value, list):
            val, msg = self._cast_to_string_list_(value)
            value = val
            if (msg != 'ok'):
                self._sim_.message(Message(self._get_error_header_()+msg,"ERROR"))
                return
        # Is a list
        for el in value:
            el = str(el)
        # Own copy: keeping the caller list would let it be mutated from
        # outside, and would be shared by every parameter assigned from it
        self._value_ = list(value)

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
        """list of Component: referenced components, None for those not found"""
        components = []
        for i, element in enumerate(self.value):
            if self.external[i]:
                splits = element.split("->")
                proj = self.parent.project()._sim_.project(splits[0])
                if proj is None:
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
                    errors.append(Message(msg,"ERROR"))
            if comps[i] is None and self.value[i] != "not_defined":
                msg = self._get_error_header_() + f"{self.value[i]} component not found."
                errors.append(Message(msg,"ERROR"))
        return errors


# _____________ Parameter_variable ___________________________


class Parameter_variable(Parameter):
    """Variable of another component, with the symbol used for it in expressions

    The value has the format "symbol = component.variable" (or
    "symbol = project->component.variable"). The component that holds the parameter gets
    a variable named `symbol` with a copy of the values, and the symbol can be used in its
    `Parameter_math_exp` expressions.
    """

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
            msg = 'Incorrect format. Expected format "symbol = component.variable"'
            self._sim_.message(Message(self._get_error_header_()+msg,"ERROR"))

    @property
    def external(self):
        return self._external_

    @property
    def symbol(self):
        return self._symbol_

    @property
    def variable(self):
        """Variable: referenced variable, None if not found"""
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
        if var is None and self._symbol_ != "not_defined":
            msg = self._get_error_header_() + f"{self.value} component or variable not found."
            errors.append(Message(msg,"ERROR"))
        return errors


class Parameter_variable_list(Parameter):
    """List of variables of other components (same format as Parameter_variable)"""

    def __init__(self, key, value=["not_defined = component.variable"]):
        Parameter.__init__(self, key, value)
        self.value = value

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        if isinstance(value, str): # Single string
            value = [value]
        if not isinstance(value, list):
            val, msg = self._cast_to_string_list_(value)
            value = val
            if (msg != 'ok'):
                self._sim_.message(Message(self._get_error_header_()+msg,"ERROR"))
                return
        # Is a list
        for el in value:
            el = str(el)
        # Own copy: keeping the caller list would let it be mutated from
        # outside, and would be shared by every parameter assigned from it
        self._value_ = list(value)

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
            msg = 'Incorrect format. Expected format "symbol = component.variable"'
            self._sim_.message(Message(self._get_error_header_()+msg,"ERROR"))

    @property
    def external(self):
        return self._external_

    @property
    def symbol(self):
        return self._symbol_

    @property
    def variable(self):
        """list of Variable: referenced variables, None for those not found"""
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
            if var is None and self.symbol[i] != "not_defined":
                msg = self._get_error_header_() + f"{self.value} component or variable not found."
                errors.append(Message(msg,"ERROR"))
        return errors


# _____________ Parameter_math_exp ___________________________


class Parameter_math_exp(Parameter):
    """Mathematical expression, evaluated during the simulation

    Python expression (the `math` module is available) in which the symbols of the
    component's `Parameter_variable` parameters can be used, e.g. "0.5 * t_ext + 10".

    Args:
        key (str): key of the parameter
        value (str, optional): expression. Defaults to "0.0".
        unit (str, optional): unit of the result. Defaults to "".
    """

    def __init__(self, key, value="0.0", unit=""):
        Parameter.__init__(self, key, value)
        self._unit_ = unit
        #self._parser_ = Parser()

    @property
    def unit(self):
        return self._unit_

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        self._value_ = str(value)

    def evaluate(self, values_dic):
        """Evaluate the expression

        Args:
            values_dic (dict): {symbol: value} of the symbols used in the expression

        Returns:
            float: result, 0 (and an error message) if the expression cannot be evaluated
        """
        try:
            val = eval(self.value,globals(),values_dic)
            return val
        except Exception as error:
            self._sim_.message(Message(self._get_error_header_()+str(error),"ERROR"))
            return 0


class Parameter_math_exp_list(Parameter):
    """List of mathematical expressions (same format as Parameter_math_exp)"""

    def __init__(self, key, value=["0.0"], unit=""):
        Parameter.__init__(self, key, value)
        self._unit_ = unit
        #self._parser_ = Parser()

    @property
    def unit(self):
        return self._unit_

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        if isinstance(value, str): # Single string
            value = [value]
        if not isinstance(value, list):
            val, msg = self._cast_to_string_list_(value)
            value = val
            if (msg != 'ok'):
                self._sim_.message(Message(self._get_error_header_()+msg,"ERROR"))
                return
        # Is a list
        for el in value:
            el = str(el)
        # Own copy: keeping the caller list would let it be mutated from
        # outside, and would be shared by every parameter assigned from it
        self._value_ = list(value)

    def evaluate(self, i, values_dic):
        """Evaluate one of the expressions

        Args:
            i (int): index of the expression in the list
            values_dic (dict): {symbol: value} of the symbols used in the expression

        Returns:
            float: result, 0 (and an error message) if the expression cannot be evaluated
        """
        try:
            val = eval(self.value[i],globals(),values_dic)
            return val
        except Exception as error:
            self._sim_.message(Message(self._get_error_header_()+str(error),"ERROR"))
            return 0
