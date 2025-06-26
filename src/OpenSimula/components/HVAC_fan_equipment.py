from OpenSimula.Parameters import Parameter_float, Parameter_math_exp
from OpenSimula.Component import Component

class HVAC_fan_equipment(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_fan_equipment"
        self.parameter("description").value = "HVAC Fan equipment manufacturer information"
        self.add_parameter(Parameter_float("nominal_air_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("nominal_pressure", 1, "Pa", min=0))
        self.add_parameter(Parameter_float("nominal_power", 1, "W", min=0))
        self.add_parameter(Parameter_math_exp("pressure_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("power_expression", "1", "frac"))

    def check(self):
        errors = super().check()
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        # Parameters
        self._nominal_air_flow = self.parameter("nominal_air_flow").value
        self._nominal_pressure = self.parameter("nominal_pressure").value
        self._nominal_power = self.parameter("nominal_power").value

    def get_pressure(self,air_flow):
        # variables dictonary 
        var_dic = {"F_air":air_flow/self._nominal_air_flow}
        # Pressure
        pressure = self._nominal_pressure * self.parameter("pressure_expression").evaluate(var_dic)
        return pressure

    def get_power(self,air_flow):
        # variables dictonary 
        var_dic = {"F_air":air_flow/self._nominal_air_flow}
        # Power
        power = self._nominal_power * self.parameter("power_expression").evaluate(var_dic)
        return power       
    
    




        