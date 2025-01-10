from OpenSimula.Parameters import Parameter_component, Parameter_float, Parameter_variable_list, Parameter_math_exp
from OpenSimula.Component import Component
from OpenSimula.Variable import Variable
import psychrolib as sicro


class HVAC_perfect_system(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_perfect_system"
        self.parameter("description").value = "HVAC Perfect system for cooling and heating load"
        self.add_parameter(Parameter_component("space", "not_defined", ["Space"])) # Space, TODO: Add Air_distribution, Energy_load
        self.add_parameter(Parameter_component("file_met", "not_defined", ["File_met"]))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("outdoor_air_flow", "0", "m³/s"))
        self.add_parameter(Parameter_math_exp("heating_setpoint", "20", "°C"))
        self.add_parameter(Parameter_math_exp("cooling_setpoint", "25", "°C"))
        self.add_parameter(Parameter_math_exp("humidifying_setpoint", "0", "%"))
        self.add_parameter(Parameter_math_exp("dehumidifying_setpoint", "100", "%"))
        self.add_parameter(Parameter_math_exp("system_on_off", "1", "on/off"))
        # Variables
        self.add_variable(Variable("Q_sensible", unit="W"))
        self.add_variable(Variable("Q_latent", unit="W"))
        self.add_variable(Variable("outdoor_air_flow", unit="m³/s"))
        self.add_variable(Variable("heating_setpoint", unit="°C"))
        self.add_variable(Variable("cooling_setpoint", unit="°C"))
        self.add_variable(Variable("humidifying_setpoint", unit="%"))
        self.add_variable(Variable("dehumidifying_setpoint", unit="%"))
        self.add_variable(Variable("system_on_off", unit="on/off"))
         # Sicro
        sicro.SetUnitSystem(sicro.SI)
        self.CP_A = 1007 # (J/kg·K)
        self.LAMBDA = 2501 # (J/g H20)

    def check(self):
        errors = super().check()
        # Test space defined
        if self.parameter("space").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, must define its space.")
        # Test file_met defined
        if self.parameter("file_met").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, file_met must be defined.")
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._space = self.parameter("space").component
        self._file_met = self.parameter("file_met").component
        self.ATM_PRESSURE = sicro.GetStandardAtmPressure(self._file_met.altitude)
        self.RHO_A = sicro.GetMoistAirDensity(20,0.0073,self.ATM_PRESSURE)
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

        # outdoor air flow
        self._outdoor_air_flow = self.parameter("outdoor_air_flow").evaluate(var_dic)
        self.variable("heating_setpoint").values[time_index] = self._outdoor_air_flow
        # setpoints
        self.variable("heating_setpoint").values[time_index] = self.parameter("heating_setpoint").evaluate(var_dic)
        self.variable("cooling_setpoint").values[time_index] = self.parameter("cooling_setpoint").evaluate(var_dic)
        self.variable("humidifying_setpoint").values[time_index] = self.parameter("humidifying_setpoint").evaluate(var_dic)
        self.variable("dehumidifying_setpoint").values[time_index] = self.parameter("dehumidifying_setpoint").evaluate(var_dic)
         # on/off
        self.variable("system_on_off").values[time_index] = self.parameter("system_on_off").evaluate(var_dic)
        if self.variable("system_on_off").values[time_index] != 0:
            self.variable("system_on_off").values[time_index] = 1

        self._T_odb = self._file_met.variable("temperature").values[time_index]
        self._w_o = self._file_met.variable("abs_humidity").values[time_index]
        self._T_cool_sp = self.variable("cooling_setpoint").values[time_index]
        self._T_heat_sp = self.variable("heating_setpoint").values[time_index]
        self._HR_min = self.variable("humidifying_setpoint").values[time_index] 
        self._HR_max = self.variable("dehumidifying_setpoint").values[time_index] 
        self._system_on = self.variable("system_on_off").values[time_index]

        # Add uncontrolled vantilation to the space
        if self._system_on:
            air_flow = {"name": self.parameter("name").value, "V": self._outdoor_air_flow, "T":self._T_odb, "w": self._w_o}
            self._space.add_uncontrol_system_air_flow(air_flow)


    def iteration(self, time_index, date, daylight_saving):
        super().iteration(time_index, date, daylight_saving)
        self._control_system = {"V": 0, "T": 0, "w":0, "Q":0, "M":0 }      
        if self._system_on: 
            self._control_system["Q"] = self._space.get_Q_required(self._T_cool_sp, self._T_heat_sp)
            self._control_system["M"] = self._space.get_M_required(self._HR_min, self._HR_max)
        self._space.set_control_system(self._control_system)
        return True
        
    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        if self._system_on:
            T_space = self._space.variable("temperature").values[time_index]
            w_space = self._space.variable("abs_humidity").values[time_index]
            self.variable("Q_sensible").values[time_index] = self._control_system["Q"]   
            self.variable("Q_latent").values[time_index] = self._control_system["M"] * self.LAMBDA


