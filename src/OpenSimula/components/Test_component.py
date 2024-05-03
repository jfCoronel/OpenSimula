from OpenSimula.Parameters import (
    Parameter_boolean,
    Parameter_float,
    Parameter_int,
    Parameter_string,
    Parameter_options,
    Parameter_component,
    Parameter_boolean_list,
    Parameter_string_list,
    Parameter_int_list,
    Parameter_float_list,
    Parameter_options_list,
    Parameter_component_list,
    Parameter_variable,
    Parameter_variable_list,
    Parameter_math_exp,
    Parameter_math_exp_list
)
from OpenSimula.Component import Component
from OpenSimula.Variable import Variable


class Test_component(Component):
    """Component for development testing"""

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Test_component"
        self.parameter("description").value = "Dummy component for testing"

        self.add_parameter(Parameter_boolean("boolean", False))
        self.add_parameter(Parameter_string("string", "Hello World"))
        self.add_parameter(Parameter_int("int", 100, "h"))
        self.add_parameter(Parameter_float("float", 0.1, "m"))
        self.add_parameter(Parameter_options(
            "options", "One", ["One", "Two", "Three"]))
        self.add_parameter(Parameter_component("component", "not_defined"))
        self.add_parameter(Parameter_variable("variable"))
        self.add_parameter(Parameter_math_exp("math_exp"))
        self.add_parameter(Parameter_boolean_list(
            "boolean_list", [True, False]))
        self.add_parameter(Parameter_string_list(
            "string_list", ["Hello World 1", "Hello World 2"]))
        self.add_parameter(Parameter_int_list("int_list", [50, 100], "h"))
        self.add_parameter(Parameter_float_list("float_list", [0.1, 0.2], "m"))
        self.add_parameter(Parameter_options_list(
            "options_list", ["One", "Two"], ["One", "Two", "Three"]))
        self.add_parameter(Parameter_component_list(
            "component_list", ["not_defined", "not_defined"]))
        self.add_parameter(Parameter_variable_list("variable_list"))
        self.add_parameter(Parameter_math_exp_list("math_exp_list"))

        # Variable
        self.add_variable(Variable("t", unit="s"))
        self.add_variable(Variable("exp_1"))
        self.add_variable(Variable("exp_2"))
        self.add_variable(Variable("exp_3"))

        self._initial_date_ = None

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self.print(
            f"Component: {self.parameter('name').value} Starting simulation ...")

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        if time_index == 0:
            self._initial_date_ = date
        self.variable("t").values[time_index] = (
            date - self._initial_date_).total_seconds()

        variables_dic = {}
        for key, var in self._variables_.items():
            variables_dic[key] = var.values[time_index]

        self.variable("exp_1").values[time_index] = self.parameter(
            "math_exp").evaluate(variables_dic)

    def post_simulation(self):
        self.print(
            f"Component: {self.parameter('name').value} Ending simulation ...")
