from opensimula.Component import Component
from opensimula.parameters import Parameter_string, Parameter_component
from opensimula.variables import Variable


class Outdoor(Component):
    def __init__(self):
        Component.__init__(self)
        self.parameter["type"].value = "Outdoor"
        self.parameter["name"].value = "Outdoor_x"
        self.add_parameter(
            Parameter_string("description", "Outdoor zone from a meteorological file")
        )
        self.add_parameter(Parameter_component("meteo_file", "not_defined"))

    def check(self):
        #
        self.parameter["meteo_file"].findComponent()
        if self.parameter["meteo_file"].component == None:
            self.message(
                "Error in component: "
                + self.parameter["name"].value
                + ", type: "
                + self.parameter["type"].value
            )
            self.message(
                "   meteo_file: "
                + self.parameter["meteo_file"].value
                + " component not found"
            )
            return 1
        else:
            return 0

    def pre_simulation(self, n_time_steps):
        self.add_variable(Variable("temperature", n_time_steps, unit="°C"))
        self.add_variable(Variable("sky_temperature", n_time_steps, unit="°C"))
        self.add_variable(Variable("abs_humidity", n_time_steps, unit="g/kg"))
        self.add_variable(Variable("sol_direct", n_time_steps, unit="W/m²"))
        self.add_variable(Variable("sol_diffuse", n_time_steps, unit="W/m²"))
        self.add_variable(Variable("wind_speed", n_time_steps, unit="m/s"))
        self.add_variable(Variable("wind_direction", n_time_steps, unit="°"))
        self.add_variable(Variable("sol_azimut", n_time_steps, unit="°"))
        self.add_variable(Variable("sol_altitude", n_time_steps, unit="°"))

    def pre_iteration(self, time_index, date):
        values = self.parameter["meteo_file"].component.get_instant_values(date)
        self.variable["temperature"].array[time_index] = values["temperature"]
        self.variable["sky_temperature"].array[time_index] = values["sky_temperature"]
        self.variable["abs_humidity"].array[time_index] = values["abs_humidity"] * 1000
        self.variable["sol_direct"].array[time_index] = values["sol_direct"]
        self.variable["sol_diffuse"].array[time_index] = values["sol_diffuse"]
        self.variable["wind_speed"].array[time_index] = values["wind_speed"]
        self.variable["wind_direction"].array[time_index] = values["wind_direction"]
        self.variable["sol_azimut"].array[time_index] = values["sol_azimut"]
        self.variable["sol_altitude"].array[time_index] = 90 - values["sol_cenit"]

    def iteration(self, time_index, date):
        return True
