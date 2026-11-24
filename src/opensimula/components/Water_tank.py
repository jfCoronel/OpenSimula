from opensimula.Component import Component
from opensimula.Parameters import Parameter_float, Parameter_math_exp, Parameter_variable_list
from opensimula.Variable import Variable


class Water_tank(Component):
    """Water storage tank: a DHW tank, an electric water heater or a buffer tank.

    Equipment data, like a Boiler: it is used by the HVAC_water_system or the
    HVAC_water_circuit that refers to it in its ``tank`` parameter, whose water is then
    the water of the tank (fully mixed, one node). Its heat losses are
    UA·(T − T_ambient), with the ambient temperature an expression (e.g. the
    temperature of the space it is in). The system that holds it stores its
    temperature and losses in the variables of the tank.
    """

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Water_tank"
        self.parameter("description").value = "Water storage tank"
        self.add_parameter(Parameter_float("volume", 150, "dm³", min=0.001))
        self.add_parameter(Parameter_float("UA", 1.5, "W/K", min=0))
        # thermostat: charging starts when the water is dead_band below the setpoint and
        # goes on up to the setpoint
        self.add_parameter(Parameter_float("dead_band", 0, "K", min=0))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("ambient_temperature", "20", "°C"))
        self.add_variable(Variable("temperature", unit="°C"))
        self.add_variable(Variable("T_ambient", unit="°C"))
        self.add_variable(Variable("Q_loss", unit="W"))  # heat lost, positive

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        var_dic = self.get_parameter_variable_dictionary(time_index)
        self.T_ambient = self.parameter("ambient_temperature").evaluate(var_dic)

    def get_dead_band(self):
        """Dead band of the thermostat (K)."""
        return self.parameter("dead_band").value

    def get_volume(self):
        """Water volume (dm³)."""
        return self.parameter("volume").value

    def get_loss(self, T):
        """Heat lost by the tank with its water at T (W, positive when it loses)."""
        return self.parameter("UA").value * (T - self.T_ambient)

    def set_state(self, time_index, T):
        """Store the temperature of the water and the losses at a time step."""
        self.variable("temperature").values[time_index] = T
        self.variable("T_ambient").values[time_index] = self.T_ambient
        self.variable("Q_loss").values[time_index] = self.get_loss(T)
