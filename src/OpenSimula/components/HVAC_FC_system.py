from OpenSimula.Iterative_process import Iterative_process
from OpenSimula.Message import Message
from OpenSimula.Parameters import Parameter_component, Parameter_float, Parameter_variable_list, Parameter_math_exp, Parameter_options
from OpenSimula.Component import Component
from OpenSimula.Variable import Variable
import psychrolib as sicro

class HVAC_FC_system(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_FC_system"
        self.parameter("description").value = "HVAC Fan Coil system for time simulation"
        self.add_parameter(Parameter_component("equipment", "not_defined", ["HVAC_FC_equipment"]))
        self.add_parameter(Parameter_component("space", "not_defined", ["Space"])) # Space
        self.add_parameter(Parameter_float("supply_air_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_math_exp("outdoor_air_flow", "0", "m³/s"))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("heating_setpoint", "20", "°C"))
        self.add_parameter(Parameter_math_exp("cooling_setpoint", "25", "°C"))
        self.add_parameter(Parameter_math_exp("system_on_off", "1", "on/off"))
        self.add_parameter(Parameter_options("water_source", "UNKNOWN", ["UNKNOWN", "WATER_LOOP"]))
        self.add_parameter(Parameter_float("cooling_water_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("heating_water_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("inlet_cooling_water_temp", 7, "ºC"))
        self.add_parameter(Parameter_float("inlet_heating_water_temp", 50, "ºC"))

        # Variables
        self.add_variable(Variable("state", unit="flag")) # 0: 0ff, 1: Heating, 2: Heating max cap, -1:Cooling, -2:Cooling max cap, 3: Venting 
        self.add_variable(Variable("T_odb", unit="°C"))
        self.add_variable(Variable("T_owb", unit="°C"))
        self.add_variable(Variable("T_idb", unit="°C"))
        self.add_variable(Variable("T_iwb", unit="°C"))
        self.add_variable(Variable("F_air", unit="frac"))
        self.add_variable(Variable("F_load", unit="frac"))
        self.add_variable(Variable("outdoor_air_flow", unit="m³/s"))
        self.add_variable(Variable("outdoor_air_fraction", unit="frac"))
        self.add_variable(Variable("T_supply", unit="°C"))
        self.add_variable(Variable("w_supply", unit="g/kg"))
        self.add_variable(Variable("T_fan_in", unit="°C"))
        self.add_variable(Variable("w_fan_in", unit="g/kg"))
        self.add_variable(Variable("Q_sensible", unit="W"))
        self.add_variable(Variable("Q_latent", unit="W"))
        self.add_variable(Variable("Q_total", unit="W"))
        self.add_variable(Variable("fan_power", unit="W"))
        self.add_variable(Variable("heating_setpoint", unit="°C"))
        self.add_variable(Variable("cooling_setpoint", unit="°C"))
        self.add_variable(Variable("epsilon", unit="frac"))
        self.add_variable(Variable("epsilon_adp", unit="frac"))
        self.add_variable(Variable("T_iw", unit="°C"))
        self.add_variable(Variable("T_ow", unit="°C"))

    def check(self):
        errors = super().check()
        # Test equipment defined
        if self.parameter("equipment").value == "not_defined":
            msg = f"{self.parameter('name').value}, must define its equipment."
            errors.append(Message(msg, "ERROR"))
        # Test space defined
        if self.parameter("space").value == "not_defined":
            msg = f"{self.parameter('name').value}, must define its space."
            errors.append(Message(msg, "ERROR"))
        # Test file_met defined
        if self.project().parameter("simulation_file_met").value == "not_defined":
            msg = f"{self.parameter('name').value}, file_met must be defined in the project 'simulation_file_met'."
            errors.append(Message(msg, "ERROR"))
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        # Sicro
        sicro.SetUnitSystem(sicro.SI)
        self.props = self._sim_.props
        self._file_met = self.project().parameter("simulation_file_met").component

        # Parameters        
        self._space = self.parameter("space").component
        self._equipment = self.parameter("equipment").component
        self._supply_air_flow = self.parameter("supply_air_flow").value
        self._f_air = self._supply_air_flow / self._equipment.parameter("nominal_air_flow").value
        # Water flows and temperatures
        self._cooling_water_flow = self.parameter("cooling_water_flow").value
        self._heating_water_flow = self.parameter("heating_water_flow").value
        self._cooling_F_water = self._cooling_water_flow/self._equipment.parameter("nominal_cooling_water_flow").value
        self._heating_F_water = self._heating_water_flow/self._equipment.parameter("nominal_heating_water_flow").value
        self._cooling_water_temp = self.parameter("inlet_cooling_water_temp").value
        self._heating_water_temp = self.parameter("inlet_heating_water_temp").value
        self._f_load = 0
        self._no_load_heat = self._equipment.get_fan_heat(0)
        self._rho_coil_in = self.props["RHO_A"] 
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
        # Outdoor air
        self._T_odb = self._file_met.variable("temperature").values[time_index]
        self._T_owb = self._file_met.variable("wet_bulb_temp").values[time_index]
        self._w_o = self._file_met.variable("abs_humidity").values[time_index]
        self.variable("T_odb").values[time_index] = self._T_odb
        self.variable("T_owb").values[time_index] = self._T_owb 
        # variables dictonary
        var_dic = {}
        for i in range(len(self.input_var_symbol)):
            var_dic[self.input_var_symbol[i]] = self.input_var_variable[i].values[time_index]
        # outdoor air flow 
        self._outdoor_air_flow = self.parameter("outdoor_air_flow").evaluate(var_dic)
        self.variable("outdoor_air_flow").values[time_index] = self._outdoor_air_flow
        self._outdoor_rho = 1/sicro.GetMoistAirVolume(self._T_odb,self._w_o/1000,self.props["ATM_PRESSURE"])
        self._m_oa = self._outdoor_air_flow * self._outdoor_rho

        # setpoints
        self._T_heat_sp = self.parameter("heating_setpoint").evaluate(var_dic)
        self.variable("heating_setpoint").values[time_index] = self._T_heat_sp
        self._T_cool_sp = self.parameter("cooling_setpoint").evaluate(var_dic)
        self.variable("cooling_setpoint").values[time_index] = self._T_cool_sp
        # on/off
        self._on_off = self.parameter("system_on_off").evaluate(var_dic)
        if self._on_off == 0:
            self._state = 0
            self.variable("state").values[time_index] = 0
            self._on_off = False
        else:
            self._on_off = True
        # Converge Supply mass air flow
        self._m_supply = self._supply_air_flow * self._rho_coil_in
        self.itera_m_supply = Iterative_process(self._m_supply,tol=1e-4)

    
    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)
        if self._on_off:
            self._T_space = self._space.variable("temperature").values[time_index]
            self._w_space = self._space.variable("abs_humidity").values[time_index]
            # Calculate Q_required
            self._calculate_required_Q()
            space_air = self._simulate_system()
            self._space.set_control_system(space_air)
            self._m_supply = self._supply_air_flow * self._rho_coil_in
            self.itera_m_supply.set_next_x(self._m_supply)
            return self.itera_m_supply.converged()
        else:
            return True

    def _calculate_required_Q(self):
        K_t,F_t = self._space.get_thermal_equation(False)
        K_ts = K_t + self._m_oa * self.props["C_PA"]
        F_ts = F_t + self._m_oa * self.props["C_PA"] * self._T_odb 
        T_flo = F_ts/K_ts
        if T_flo > self._T_cool_sp:
            self._Q_required =  K_ts * self._T_cool_sp - F_ts
        elif T_flo < self._T_heat_sp:
            self._Q_required =  K_ts * self._T_heat_sp - F_ts
        else: 
            self._Q_required = 0
        if abs(self._Q_required) < 0.0001: # Problems with convergence
            self._Q_required = 0


    def _mix_air(self, f, T1, w1, T2, w2):
        T = f * T1 + (1-f)*T2
        w = f * w1 + (1-f)*w2
        if (T > 100):
            T_wb = 50 # Inventado
        else:
            T_wb = sicro.GetTWetBulbFromHumRatio(T,w/1000,self.props["ATM_PRESSURE"])
        return (T,w,T_wb)        
    
    def _simulate_system(self):
        # Venting
        state = 3
        f_load = 0
        Q_sen = self._no_load_heat
        M_w = 0

        self._T_idb, self._w_i, self._T_iwb = self._mix_air(self._m_oa/self._m_supply, self._T_odb, self._w_o, self._T_space, self._w_space)
        self._rho_coil_in = 1/sicro.GetMoistAirVolume(self._T_idb,self._w_i/1000,self.props["ATM_PRESSURE"])

        if self._Q_required > 0: # Heating    
            Q_sen, Q_coil, f_load = self._equipment.get_heating_load(self._T_idb, self._T_iwb, self._heating_water_temp,self._f_air,self._heating_F_water,self._Q_required)
            if f_load == 1:
                state = 1
            else:
                state = 2
        elif self._Q_required < 0: # Cooling
            Q_tot, Q_sen, Q_coil, f_load = self._equipment.get_cooling_load(self._T_idb, self._T_iwb,self._cooling_water_temp,self._f_air,self._cooling_F_water,self._Q_required)
            if f_load == 1:
                state = -2
            else:
                state = -1
            M_w = -(Q_tot - Q_sen) / self.props["LAMBDA"]
            Q_sen = -Q_sen
            Q_coil = -Q_coil

        self._state = state
        self._Q_sen = Q_sen
        self._M_w = M_w
        self._f_load = f_load
        self._Q_coil = Q_coil

        air_flow = {"M_a": self._m_oa,
                    "T_a": self._T_odb,
                    "w_a":self._w_o, 
                    "Q_s":Q_sen, 
                    "M_w":M_w }
        return air_flow                    

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        self.variable("state").values[time_index] = self._state
        if self._state != 0 : # on
            self.variable("T_idb").values[time_index] = self._T_idb
            self.variable("T_iwb").values[time_index] = self._T_iwb
            self.variable("outdoor_air_fraction").values[time_index] = self._m_oa/self._m_supply
            # Density of air at the fan inlet
            T_fan_in = self._Q_coil/(self._m_supply*self.props["C_PA"]) + self._T_idb
            w_fan_in = self._M_w/self._m_supply +self._w_i
            self.variable("T_fan_in").values[time_index] = T_fan_in
            self.variable("w_fan_in").values[time_index] = w_fan_in
            self.variable("T_supply").values[time_index] = self._Q_sen/(self._m_supply*self.props["C_PA"]) + self._T_idb
            self.variable("w_supply").values[time_index] = w_fan_in
            self.variable("F_air").values[time_index] = self._f_air
            self.variable("F_load").values[time_index] = self._f_load
            fan_power = self._equipment.get_fan_power(self._f_load)
            self.variable("fan_power").values[time_index] = fan_power
            if self._state == 1 or self._state == 2: # Heating
                Q_sys = self._Q_sen - fan_power
                self.variable("Q_sensible").values[time_index] = Q_sys
                self.variable("Q_total").values[time_index] = Q_sys
                self.variable("T_iw").values[time_index] = self._heating_water_temp
                self.variable("T_ow").values[time_index] = self._heating_water_temp - Q_sys/(self._heating_water_flow * self.props["RHOCP_W"](self._heating_water_temp))                    
            elif self._state == -1 or self._state == -2: #Cooling
                Q_s = -self._Q_sen + fan_power
                Q_l = self._M_w * self.props["LAMBDA"]
                self.variable("Q_sensible").values[time_index] = Q_s
                self.variable("Q_latent").values[time_index] = Q_l
                self.variable("Q_total").values[time_index] = Q_s
                self.variable("T_iw").values[time_index] = self._cooling_water_temp
                self.variable("T_ow").values[time_index] = self._cooling_water_temp + (Q_s+Q_l)/(self._cooling_water_flow * self.props["RHOCP_W"](self._cooling_water_temp))                
