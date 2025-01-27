from OpenSimula.Parameters import Parameter_component, Parameter_float, Parameter_variable_list, Parameter_math_exp, Parameter_options
from OpenSimula.Component import Component
from OpenSimula.Variable import Variable
import psychrolib as sicro


class HVAC_DX_system(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_DX_system"
        self.parameter("description").value = "HVAC Direct Expansion system for time simulation"
        self.add_parameter(Parameter_component("equipment", "not_defined", ["HVAC_DX_equipment"]))
        self.add_parameter(Parameter_component("space", "not_defined", ["Space"])) # Space, TODO: Add Air_distribution, Energy_load
        self.add_parameter(Parameter_component("file_met", "not_defined", ["File_met"]))
        self.add_parameter(Parameter_float("supply_air_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("outdoor_air_flow", 0, "m³/s", min=0))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("heating_setpoint", "20", "°C"))
        self.add_parameter(Parameter_math_exp("cooling_setpoint", "25", "°C"))
        self.add_parameter(Parameter_math_exp("system_on_off", "1", "on/off"))
        self.add_parameter(Parameter_options("control_type", "PERFECT", ["PERFECT", "TEMPERATURE"]))
        self.add_parameter(Parameter_float("cooling_bandwidth", 1, "ºC", min=0))
        self.add_parameter(Parameter_float("heating_bandwidth", 1, "ºC", min=0))
        self.add_parameter(Parameter_float("relaxing_coefficient", 0.1, "frac", min=0, max=1))

        # Variables
        self.add_variable(Variable("state", unit="flag")) # 0: 0ff, 1: Heating, 2: Cooling, 3: Venting 
        self.add_variable(Variable("T_odb", unit="°C"))
        self.add_variable(Variable("T_owb", unit="°C"))
        self.add_variable(Variable("T_idb", unit="°C"))
        self.add_variable(Variable("T_iwb", unit="°C"))
        self.add_variable(Variable("F_air", unit="frac"))
        self.add_variable(Variable("F_load", unit="frac"))
        self.add_variable(Variable("T_supply", unit="°C"))
        self.add_variable(Variable("w_supply", unit="°C"))
        self.add_variable(Variable("Q_sensible", unit="W"))
        self.add_variable(Variable("Q_latent", unit="W"))
        self.add_variable(Variable("power", unit="W"))
        self.add_variable(Variable("heating_setpoint", unit="°C"))
        self.add_variable(Variable("cooling_setpoint", unit="°C"))
        self.add_variable(Variable("EER", unit="frac"))
        self.add_variable(Variable("COP", unit="frac"))


         # Sicro
        sicro.SetUnitSystem(sicro.SI)
        self.CP_A = 1007 # (J/kg·K)
        self.DH_W = 2501 # (J/g H20)

    def check(self):
        errors = super().check()
        # Test equipment defined
        if self.parameter("equipment").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, must define its equipment.")
        # Test space defined
        if self.parameter("space").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, must define its space.")
        # Test file_met defined
        if self.parameter("file_met").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, file_met must be defined.")
         # Test outdoor_air_flow
        if self.parameter("outdoor_air_flow").value > self.parameter("supply_air_flow").value:
            errors.append(
                f"Error: {self.parameter('name').value}, outdoor_air_flow must be less than supply_air_flow.")
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._equipment = self.parameter("equipment").component
        self._space = self.parameter("space").component
        self._file_met = self.parameter("file_met").component
        self._supply_air_flow = self.parameter("supply_air_flow").value
        self._outdoor_air_flow = self.parameter("outdoor_air_flow").value
        self._f_air = self._supply_air_flow / self._equipment.parameter("nominal_air_flow").value
        self._f_oa = self._outdoor_air_flow/self._supply_air_flow
        self.ATM_PRESSURE = sicro.GetStandardAtmPressure(self._file_met.altitude)
        self.RHO_A = sicro.GetMoistAirDensity(20,0.0073,self.ATM_PRESSURE)
        self._m_supply =  self.RHO_A * self._supply_air_flow # V_imp * rho 
        self._mrcp =  self.RHO_A * self._supply_air_flow * self.CP_A # V_imp * rho * c_p
        self._mrdh =  self.RHO_A * self._supply_air_flow * self.DH_W # V_imp * rho * Dh
        self._cool_band = self.parameter("cooling_bandwidth").value
        self._heat_band = self.parameter("heating_bandwidth").value
        # input_varibles symbol and variable
        self.input_var_symbol = []
        self.input_var_variable = []
        for i in range(len(self.parameter("input_variables").variable)):
            self.input_var_symbol.append(
                self.parameter("input_variables").symbol[i])
            self.input_var_variable.append(
                self.parameter("input_variables").variable[i])
        self._f_load = 0
        self._r_coef = self.parameter("relaxing_coefficient").value

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        # Outdoor air
        self._T_odb = self._file_met.variable("temperature").values[time_index]
        self._T_owb = self._file_met.variable("wet_bulb_temp").values[time_index]
        self._w_o = self._file_met.variable("abs_humidity").values[time_index]
        self.variable("T_odb").values[time_index] = self._T_odb
        self.variable("T_owb").values[time_index] = self._T_owb
        # Control
        # variables dictonary
        var_dic = {}
        for i in range(len(self.input_var_symbol)):
            var_dic[self.input_var_symbol[i]] = self.input_var_variable[i].values[time_index]

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
        self._f_load_pre = self._f_load
    
    def iteration(self, time_index, date, daylight_saving):
        super().iteration(time_index, date, daylight_saving)
        if self._on_off:
            self._control_system = {"V": self._supply_air_flow, "T": 0, "w":0, "Q":0, "M":0 }
            self._T_space = self._space.variable("temperature").values[time_index]
            self._w_space = self._space.variable("abs_humidity").values[time_index]
            # Mix air
            self._T_idb, self._w_i, self._T_iwb = self._mix_air(self._f_oa, self._T_odb, self._w_o, self._T_space, self._w_space)
            if self.parameter("control_type").value == "PERFECT":
                Q_required = self._space.get_Q_required(self._T_cool_sp, self._T_heat_sp)
                self._perfect_control(Q_required)    
            elif self.parameter("control_type").value == "TEMPERATURE":
                self._air_temperature_control()
            self._control_system["T"] = self._T_supply
            self._control_system["w"] = self._w_supply
            self._space.set_control_system(self._control_system)
        return True

    def _mix_air(self, f, T1, w1, T2, w2):
        T = f * T1 + (1-f)*T2
        w = f * w1 + (1-f)*w2
        return (T,w,sicro.GetTWetBulbFromHumRatio(T,w/1000,self.ATM_PRESSURE))        
    
    def _perfect_control(self, Q_required):
        # Venting
        self._f_load = 0
        self._state = 3
        self._T_supply = self._T_idb
        self._w_supply = self._w_i
        self._Q_sen = 0
        if Q_required > 0: # Heating    
            heat_cap = self._equipment.get_heating_capacity(self._T_idb, self._T_iwb, self._T_odb, self._T_owb,self._f_air)
            if heat_cap > 0:
                self._T_supply = Q_required / self._mrcp + self._T_space
                self._Q_sen = self._mrcp * (self._T_supply - self._T_idb)
                self._f_load = self._Q_sen/heat_cap
                self._state = 1
                if self._f_load > 1:
                    self._Q_sen = heat_cap
                    self._f_load = 1
                    self._T_supply = self._T_idb + self._Q_sen / self._mrcp
                self._w_supply = self._w_i
        elif Q_required < 0: # Cooling
            tot_cool_cap, sen_cool_cap = self._equipment.get_cooling_capacity(self._T_idb, self._T_iwb, self._T_odb,self._T_owb,self._f_air)
            if sen_cool_cap > 0:
                self._T_supply = self._T_space + Q_required / self._mrcp
                self._Q_sen  = self._mrcp * (self._T_idb - self._T_supply)
                self._f_load = -self._Q_sen/sen_cool_cap
                self._state = 2
                if self._f_load < -1:
                    self._Q_sen = sen_cool_cap
                    self._f_load = -1
                    self._T_supply = self._T_idb - self._Q_sen / self._mrcp
                self._Q_total = -tot_cool_cap*self._f_load
                self._w_supply = self._w_i - (self._Q_total - self._Q_sen) / self._mrdh         
                        
    def _air_temperature_control(self):
        if (self._T_space >= self._T_cool_sp + self._cool_band/2):
            f_load = -1
        elif (self._T_space >= self._T_cool_sp - self._cool_band/2):
            f_load = ((self._T_cool_sp - self._cool_band/2)-self._T_space ) / self._cool_band    
        elif (self._T_space >= self._T_heat_sp + self._heat_band/2):
            f_load = 0
        elif (self._T_space >= self._T_heat_sp - self._heat_band/2):
            f_load = ((self._T_heat_sp + self._heat_band/2) - self._T_space) / self._heat_band
        else:
            f_load = 1

        self._f_load = self._r_coef * f_load + (1-self._r_coef)*self._f_load_pre
        self._f_load_pre = self._f_load

        # Supply air
        # Venting
        self._T_supply = self._T_idb
        self._w_supply = self._w_i
        self._Q_sen = 0
        self._state = 3
        if self._f_load > 0: # Heating
            heat_cap = self._equipment.get_heating_capacity(self._T_idb, self._T_iwb, self._T_odb, self._T_owb,self._f_air)
            if heat_cap > 0:
                self._Q_sen = heat_cap * self._f_load
                self._T_supply = self._Q_sen / self._mrcp + self._T_idb
                self._w_supply = self._w_i
                self._state = 1
            else:
                self._state = 3
                self._f_load = 0
        elif self._f_load < 0: # Cooling
            tot_cool_cap, sen_cool_cap = self._equipment.get_cooling_capacity(self._T_idb, self._T_iwb, self._T_odb,self._T_owb, self._f_air)
            if sen_cool_cap > 0:
                self._Q_sen = -sen_cool_cap * self._f_load
                self._Q_tot = -tot_cool_cap*self._f_load           
                self._T_supply = self._T_idb - self._Q_sen / self._mrcp
                self._w_supply = self._w_i - (self._Q_tot - self._Q_sen) / self._mrdh 
                self._state = 2
            else:
                self._state = 3
                self._f_load = 0

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        self.variable("state").values[time_index] = self._state
        if self._state != 0 : # on
            self.variable("T_idb").values[time_index] = self._T_idb
            self.variable("T_iwb").values[time_index] = self._T_iwb
            self.variable("T_supply").values[time_index] = self._T_supply
            self.variable("w_supply").values[time_index] = self._w_supply
            self.variable("F_air").values[time_index] = self._f_air
            self.variable("F_load").values[time_index] = self._f_load
            if self._state == 1: # Heating
                Q,power = self._equipment.get_heating_state(self._T_idb,self._T_iwb,self._T_odb,self._T_owb,self._f_air,self._f_load)
                self.variable("Q_sensible").values[time_index] = Q
                self.variable("power").values[time_index] = power
                if power>0:
                    self.variable("COP").values[time_index] = Q/power
            elif self._state == 2: #Cooling
                Q_t,Q_s,power = self._equipment.get_cooling_state(self._T_idb,self._T_iwb,self._T_odb,self._T_owb,self._f_air,-self._f_load)
                self.variable("Q_sensible").values[time_index] = -Q_s
                self.variable("Q_latent").values[time_index] = -(Q_t - Q_s)
                self.variable("power").values[time_index] = power
                if power>0:
                    self.variable("EER").values[time_index] = Q_t/power