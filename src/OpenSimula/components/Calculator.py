from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_variable_list, Parameter_math_exp_list, Parameter_string_list
from OpenSimula.Variable import Variable


class Calculator(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Calculator"
        self.parameter(
            "description").value = "Component to perform calculations with variables from other components."
        # Parameters
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_string_list("output_variables", []))
        self.add_parameter(Parameter_string_list("output_units", []))
        self.add_parameter(Parameter_math_exp_list("output_expressions", []))

    def check(self):
        self._variables_ = {}  # Delete all the variables
        errors = super().check()
        if (
            len(self.parameter("output_variables").value)
            != len(self.parameter("output_expressions").value) or len(self.parameter("output_variables").value)
            != len(self.parameter("output_units").value)
        ):
            errors.append(
                f"Error: {self.parameter('name').value}, output_variables, output_units and output_expressions size must be equal"
            )
        else:
            # Create output variables
            for i in range(len(self.parameter("output_variables").value)):
                name = self.parameter("output_variables").value[i]
                unit = self.parameter("output_units").value[i]
                desc = self.parameter("output_expressions").value[i]
                self.add_variable(Variable(name, unit, desc))

        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        # input_varibles symbol and variable
        self.input_var_symbol = []
        self.input_var_variable = []
        for i in range(len(self.parameter("input_variables").variable)):
            self.input_var_symbol.append(
                self.parameter("input_variables").symbol[i])
            self.input_var_variable.append(
                self.parameter("input_variables").variable[i])

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        # variables dictonary
        var_dic = {}
        for i in range(len(self.input_var_symbol)):
            var_dic[self.input_var_symbol[i]
                    ] = self.input_var_variable[i].values[time_index]

        # Output variables
        for i in range(len(self.parameter("output_variables").value)):
            calculated_value = self.parameter(
                "output_expressions").evaluate(i, var_dic)
            name = self.parameter("output_variables").value[i]
            self.variable(name).values[time_index] = calculated_value
