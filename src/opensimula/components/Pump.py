from opensimula.Parameters import Parameter_float, Parameter_math_exp
from opensimula.Component import Component

class Pump(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Pump"
        self.parameter("description").value = "Pump equipment manufacturer information"
        self.add_parameter(Parameter_float("nominal_water_flow", 1, "dm³/s", min=0))
        self.add_parameter(Parameter_float("nominal_pressure", 1, "Pa", min=0))
        self.add_parameter(Parameter_float("nominal_power", 1, "W", min=0))
        self.add_parameter(Parameter_float("power_to_heat_fraction", 1, "frac", min=0, max=1))
        self.add_parameter(Parameter_math_exp("pressure_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("power_expression", "1", "frac"))

    def check(self):
        errors = super().check()
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        # Parameters
        self._nominal_water_flow = self.parameter("nominal_water_flow").value
        self._nominal_pressure = self.parameter("nominal_pressure").value
        self._nominal_power = self.parameter("nominal_power").value

    def get_pressure(self,water_flow):
        # variables dictonary 
        var_dic = {"F_water":water_flow/self._nominal_water_flow}
        # Pressure
        pressure = self._nominal_pressure * self.parameter("pressure_expression").evaluate(var_dic)
        return pressure

    def get_power(self,water_flow):
        # variables dictonary 
        var_dic = {"F_water":water_flow/self._nominal_water_flow}
        # Power
        power = self._nominal_power * self.parameter("power_expression").evaluate(var_dic)
        return power      

    def get_heat_gain(self,water_flow):
        power = self.get_power(water_flow)
        heat_gain = power * self.parameter("power_to_heat_fraction").value
        return heat_gain 
    
    




        

def staged_pump_flows(pumps, flow):
    """Flow of each pump of a group that moves a flow with staging.

    In the order of the list, as many pumps run as needed for their nominal flows to
    add up to the flow; those running share it in proportion to their nominal flow.

    Args:
        pumps (list): Pump components.
        flow (float): flow to move (dm³/s).

    Returns:
        list: flow of each pump (dm³/s), 0 for those stopped.
    """
    nominal = [p.parameter("nominal_water_flow").value for p in pumps]
    flows = [0.0] * len(pumps)
    if flow <= 0 or not pumps:
        return flows
    n, total = 0, 0.0
    for f in nominal:
        n += 1
        total += f
        if total >= flow:
            break
    if total <= 0:
        return flows
    for i in range(n):
        flows[i] = flow * nominal[i] / total
    return flows
