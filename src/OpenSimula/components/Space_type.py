from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_float, Parameter_math_exp, Parameter_variable_list
from OpenSimula.Variable import Variable


class Space_type(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Space_type"
        self.parameter(
            "description").value = "Type of space, internal gains definition"
        # Parameters
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("people_density", "0.1", "p/m²"))
        self.add_parameter(Parameter_float(
            "people_sensible", 70, "W/p", min=0))
        self.add_parameter(Parameter_float("people_latent", 35, "W/p", min=0))
        self.add_parameter(Parameter_float(
            "people_radiant_fraction", 0.6, "frac", min=0, max=1))
        self.add_parameter(Parameter_math_exp("light_density", "10", "W/m²"))
        self.add_parameter(Parameter_float(
            "light_radiant_fraction", 0.6, "frac", min=0, max=1))
        self.add_parameter(Parameter_math_exp(
            "other_gains_density", "10", "W/m²"))
        self.add_parameter(Parameter_float(
            "other_gains_latent_fraction", 0.0, "frac", min=0, max=1))
        self.add_parameter(Parameter_float(
            "other_gains_radiant_fraction", 0.5, "frac", min=0, max=1))
        self.add_parameter(Parameter_math_exp("infiltration", "1", "1/h"))

        # Variables
        self.add_variable(Variable("people_convective", unit="W/m²"))
        self.add_variable(Variable("people_radiant", unit="W/m²"))
        self.add_variable(Variable("people_latent", unit="W/m²"))
        self.add_variable(Variable("light_convective", unit="W/m²"))
        self.add_variable(Variable("light_radiant", unit="W/m²"))
        self.add_variable(Variable("other_gains_convective", unit="W/m²"))
        self.add_variable(Variable("other_gains_radiant", unit="W/m²"))
        self.add_variable(Variable("other_gains_latent", unit="W/m²"))
        self.add_variable(Variable("infiltration_rate", unit="1/h"))

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
            var_dic[self.input_var_symbol[i]] = self.input_var_variable[i].values[time_index]

        # People
        people = self.parameter("people_density").evaluate(var_dic)
        self.variable("people_convective").values[time_index] = (people * self.parameter(
            "people_sensible").value * (1 - self.parameter("people_radiant_fraction").value))
        self.variable("people_radiant").values[time_index] = (people * self.parameter(
            "people_sensible").value * self.parameter("people_radiant_fraction").value)
        self.variable("people_latent").values[time_index] = (
            people * self.parameter("people_latent").value)

        # Light
        light = self.parameter("light_density").evaluate(var_dic)
        self.variable("light_convective").values[time_index] = light * (
            1 - self.parameter("light_radiant_fraction").value)
        self.variable("light_radiant").values[time_index] = light * \
            self.parameter("light_radiant_fraction").value

        # Other gains
        other = self.parameter("other_gains_density").evaluate(var_dic)
        self.variable("other_gains_convective").values[time_index] = other * (1 - self.parameter(
            "other_gains_latent_fraction").value) * (1 - self.parameter("other_gains_radiant_fraction").value)

        self.variable("other_gains_radiant").values[time_index] = other * (1 - self.parameter(
            "other_gains_latent_fraction").value) * self.parameter("other_gains_radiant_fraction").value

        self.variable("other_gains_latent").values[time_index] = other * self.parameter(
            "other_gains_latent_fraction").value

        # Infiltration
        self.variable("infiltration_rate").values[time_index] = self.parameter(
            "infiltration").evaluate(var_dic)
        

