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
        self.add_parameter(Parameter_float("outdoor_air_flow", 0, "m³/s", min=0))
        self.add_parameter(Parameter_float("air_delta_T", 10, "ºC", min=0))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("heating_setpoint", "20", "°C"))
        self.add_parameter(Parameter_math_exp("cooling_setpoint", "25", "°C"))
        self.add_parameter(Parameter_math_exp("heating_on_off", "1", "on/off"))
        self.add_parameter(Parameter_math_exp("cooling_on_off", "1", "on/off"))
        # Variables
        self.add_variable(Variable("T_supply", unit="°C"))
        self.add_variable(Variable("w_supply", unit="°C"))
        self.add_variable(Variable("Qt_cool", unit="W"))
        self.add_variable(Variable("Qs_cool", unit="W"))
        self.add_variable(Variable("heating_setpoint", unit="°C"))
        self.add_variable(Variable("cooling_setpoint", unit="°C"))
        self.add_variable(Variable("heating_on_off", unit="on/off"))
        self.add_variable(Variable("cooling_on_off", unit="on/off"))
         # Sicro
        sicro.SetUnitSystem(sicro.SI)
        self.CP_A = 1007 # (J/kg�K)
        self.DH_W = 2501 # (J/g H20)

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
        self._space_type = self._space.parameter("space_type").component
        self._file_met = self.parameter("file_met").component
        self._outdoor_air_flow = self.parameter("outdoor_air_flow").value
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

        # setpoints
        self.variable("heating_setpoint").values[time_index] = self.parameter("heating_setpoint").evaluate(var_dic)
        self.variable("cooling_setpoint").values[time_index] = self.parameter("cooling_setpoint").evaluate(var_dic)
         # on/off
        self.variable("heating_on_off").values[time_index] = self.parameter("heating_on_off").evaluate(var_dic)
        if self.variable("heating_on_off").values[time_index] != 0:
            self.variable("heating_on_off").values[time_index] = 1
        self.variable("cooling_on_off").values[time_index] = self.parameter("cooling_on_off").evaluate(var_dic)
        if self.variable("cooling_on_off").values[time_index] != 0:
            self.variable("cooling_on_off").values[time_index] = 1

        self._T_odb = self._file_met.variable("temperature").values[time_index]
        self._T_owb = self._file_met.variable("wet_bulb_temp").values[time_index]
        self._w_o = self._file_met.variable("abs_humidity").values[time_index]
        self._T_cool_sp = self.variable("cooling_setpoint").values[time_index]
        self._T_heat_sp = self.variable("heating_setpoint").values[time_index]
        self._cool_on = self.variable("cooling_on_off").values[time_index]
        self._heat_on = self.variable("heating_on_off").values[time_index]
    

    ## POR AQUI _______

    def iteration(self, time_index, date, daylight_saving):
        super().iteration(time_index, date, daylight_saving)
        if (not self._cool_on) and (not self._heat_on): # Off
            self._state = 0
            return True
        else:
            self._T_space = self._space.variable("temperature").values[time_index]
            self._w_space = self._space.variable("abs_humidity").values[time_index]
            # Entering air
            self._T_edb, self._w_e, self._T_ewb = self._mix_air(self._f_oa,self._T_odb,self._w_o,self._T_space,self._w_space)
            if self._perfect_conditioning: # Get load needed by the space
                self._Q_heating = self._space.variable("Q_heating").values[time_index]
                self._Q_cooling = self._space.variable("Q_cooling").values[time_index]
                self.perfect_control()
            else:
                self.termostat_control()
             
             # First iteration not converged
            if self._first_iteration:
                self._first_iteration = False
                return False
            else:
                return True
            
    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        if self._state != 0 : # on
            self.variable("T_edb").values[time_index] = self._T_edb
            self.variable("T_ewb").values[time_index] = self._T_ewb
            self.variable("T_supply").values[time_index] = self._T_supply
            self.variable("w_supply").values[time_index] = self._w_supply
            self.variable("F_air").values[time_index] = self._f_air
            self.variable("F_load").values[time_index] = self._f_load
            self.variable("F_oa").values[time_index] = self._f_oa
            if self._state == 1 : # Heating
                self.variable("Q_heat").values[time_index] = self._Q_heating
                comp_power, fan_power, other_power = self._equipment.get_heating_power(self._T_edb,self._T_odb,self._T_owb,self._f_air,self._f_load)
                self.variable("Pcomp_heat").values[time_index] = comp_power
                self.variable("Pfan_heat").values[time_index] = fan_power
                self.variable("Pother_heat").values[time_index] = other_power
                self.variable("P_heat").values[time_index] = comp_power + fan_power + other_power
                self.variable("COP").values[time_index] = self._Q_heating / (comp_power + fan_power + other_power)
            elif self._state == 2 : # Cooling
                self.variable("Qt_cool").values[time_index] = self._Q_cooling_tot
                self.variable("Qs_cool").values[time_index] = self._Q_cooling
                comp_power, fan_power, other_power = self._equipment.get_cooling_power(self._T_edb,self._T_ewb,self._T_odb,self._f_air,self._f_load)
                self.variable("Pcomp_cool").values[time_index] = comp_power
                self.variable("Pfan_cool").values[time_index] = fan_power
                self.variable("Pother_cool").values[time_index] = other_power
                self.variable("P_cool").values[time_index] = comp_power + fan_power + other_power
                self.variable("EER").values[time_index] = self._Q_cooling_tot / (comp_power + fan_power + other_power)    
