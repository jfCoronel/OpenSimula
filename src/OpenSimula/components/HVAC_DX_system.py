from OpenSimula.Message import Message
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
        self.add_parameter(Parameter_component("spaces", "not_defined", ["Space"])) # Space, TODO: Add Air_distribution, Energy_load
        self.add_parameter(Parameter_float("air_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_math_exp("outdoor_air_fraction", "0", "frac"))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("heating_setpoint", "20", "°C"))
        self.add_parameter(Parameter_math_exp("cooling_setpoint", "25", "°C"))
        self.add_parameter(Parameter_math_exp("system_on_off", "1", "on/off"))
        self.add_parameter(Parameter_options("economizer", "NO", ["NO", "TEMPERATURE","TEMPERATURE_NOT_INTEGRATED","ENTHALPY","ENTHALPY_LIMITED"]))
        self.add_parameter(Parameter_float("economizer_DT", 0, "ºC", min=0))
        self.add_parameter(Parameter_float("economizer_enthalpy_limit", 0, "kJ/kg", min=0))
        
        # Variables
        self.add_variable(Variable("state", unit="flag")) # 0: 0ff, 1: Heating, 2: Heating max cap, -1:Cooling, -2:Cooling max cap, 3: Venting 
        self.add_variable(Variable("T_OA", unit="°C"))
        self.add_variable(Variable("T_OAwb", unit="°C"))
        self.add_variable(Variable("T_MA", unit="°C"))
        self.add_variable(Variable("T_MAwb", unit="°C"))
        self.add_variable(Variable("F_air", unit="frac"))
        self.add_variable(Variable("F_load", unit="frac"))
        self.add_variable(Variable("outdoor_air_fraction", unit="frac"))
        self.add_variable(Variable("m_air_flow", unit="kg/s"))
        self.add_variable(Variable("T_SA", unit="°C"))
        self.add_variable(Variable("w_SA", unit="g/kg"))
        self.add_variable(Variable("Q_total", unit="W"))
        self.add_variable(Variable("Q_sensible", unit="W"))
        self.add_variable(Variable("Q_latent", unit="W"))
        self.add_variable(Variable("power", unit="W"))
        self.add_variable(Variable("indoor_fan_power", unit="W"))
        self.add_variable(Variable("heating_setpoint", unit="°C"))
        self.add_variable(Variable("cooling_setpoint", unit="°C"))
        self.add_variable(Variable("EER", unit="frac"))
        self.add_variable(Variable("COP", unit="frac"))
        self.add_variable(Variable("efficiency_degradation", unit="frac"))


    def check(self):
        errors = super().check()
        # Test equipment defined
        if self.parameter("equipment").value == "not_defined":
            msg = f"{self.parameter('name').value}, must define its equipment."
            errors.append(Message(msg, "ERROR"))
        # Test space defined
        if self.parameter("spaces").value == "not_defined":
            msg = f"{self.parameter('name').value}, must define its space."
            errors.append(Message(msg, "ERROR"))
        # Test file_met defined
        if self.project().parameter("simulation_file_met").value == "not_defined":
            msg = f"{self.parameter('name').value}, file_met must be defined in the project 'simulation_file_met'."
            errors.append(Message(msg, "ERROR"))
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._equipment = self.parameter("equipment").component
        self._space = self.parameter("spaces").component
        self._file_met = self.project().parameter("simulation_file_met").component
        sicro.SetUnitSystem(sicro.SI)
        self.props = self._sim_.props
        self._air_flow = self.parameter("air_flow").value
        self._f_air = self._air_flow / self._equipment.parameter("nominal_air_flow").value
        self._f_load = 0
        self._no_load_heat = self._equipment.get_fan_heat(0)
        self._rho_i = self.props["RHO_A"] 
        self._economizer = self.parameter("economizer").value != "NO"
        self._economizer_DT = self.parameter("economizer_DT").value

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        # Outdoor air
        self._T_odb = self._file_met.variable("temperature").values[time_index]
        self._T_owb = self._file_met.variable("wet_bulb_temp").values[time_index]
        self._w_o = self._file_met.variable("abs_humidity").values[time_index]
        self.variable("T_OA").values[time_index] = self._T_odb
        self.variable("T_OAwb").values[time_index] = self._T_owb
        self._outdoor_rho = 1/sicro.GetMoistAirVolume(self._T_odb,self._w_o/1000,self.props["ATM_PRESSURE"])
        # variables dictonary
        var_dic = self.get_parameter_variable_dictionary(time_index)

        # outdoor air fraction
        self._outdoor_air_fraction = self.parameter("outdoor_air_fraction").evaluate(var_dic)
        self._f_oa = self._outdoor_air_fraction

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
    
    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)
        space_air = {"M_a": 0, "T_a": 0, "w_a":0, "Q_s":0, "M_w":0 }
        if self._on_off:
            self._T_space = self._space.variable("temperature").values[time_index]
            self._w_space = self._space.variable("abs_humidity").values[time_index]
            # Calculate Q_required
            self._calculate_required_Q()
            if (self._economizer):
                self._simulate_economizer() # Calculation of new f_oa
                self._calculate_required_Q()
            space_air = self._simulate_system()           
        self._space.set_control_system(space_air)
        return True

    def _calculate_required_Q(self):
        K_t,F_t = self._space.get_thermal_equation(False)
        m_cp_oa = self._air_flow * self._f_oa * self._rho_i * self.props["C_PA"]
        K_ts = K_t + m_cp_oa
        F_ts = F_t + m_cp_oa * self._T_odb + self._no_load_heat
        T_flo = F_ts/K_ts
        if T_flo > self._T_cool_sp:
            self._Q_required =  K_ts * self._T_cool_sp - F_ts
        elif T_flo < self._T_heat_sp:
            self._Q_required =  K_ts * self._T_heat_sp - F_ts
        else: 
            self._Q_required = 0
        if abs(self._Q_required) < 0.0001: # Problems with convergence
            self._Q_required = 0
    
    def _simulate_economizer(self): 
        if (self.parameter("economizer").value == "TEMPERATURE" or self.parameter("economizer").value == "TEMPERATURE_NOT_INTEGRATED"):
            on_economizer = self._T_odb < self._T_space-self._economizer_DT
        elif (self.parameter("economizer").value == "ENTHALPY"):
            h_odb = sicro.GetMoistAirEnthalpy(self._T_odb,self._w_o/1000)
            h_space = sicro.GetMoistAirEnthalpy(self._T_space,self._w_space/1000)
            on_economizer = h_odb < h_space
        elif (self.parameter("economizer").value == "ENTHALPY_LIMITED"):
            h_odb = sicro.GetMoistAirEnthalpy(self._T_odb,self._w_o/1000)
            on_economizer = h_odb < self.parameter("economizer_enthalpy_limit").value * 1000
            
        if (on_economizer):
            if (self._Q_required < 0):
                mrhocp =  self._air_flow * self.props["C_PA"]* self._outdoor_rho
                Q_rest_ae = mrhocp * (1-self._f_oa) * (self._T_odb - self._T_space)
                if  Q_rest_ae < self._Q_required:
                    self._f_oa += self._Q_required/(mrhocp * (self._T_odb-self._T_space))
                    self._Q_required = 0
                else:        
                    if (self.parameter("economizer").value == "TEMPERATURE_NOT_INTEGRATED"):
                        self._f_oa = self._outdoor_air_fraction
                    else:
                        self._f_oa = 1
            elif (self._Q_required > 0): # Heating 
                self._f_oa = self._outdoor_air_fraction
        else:
            self._f_oa = self._outdoor_air_fraction
    
    def _simulate_system(self):
        # Venting
        state = 3
        f_load = 0
        Q_coil = 0
        Q_eq = self._equipment.get_fan_heat(0)
        M_w = 0

        self._T_idb, self._w_i, self._T_iwb = self._mix_air(self._f_oa, self._T_odb, self._w_o, self._T_space, self._w_space)
        self._rho_i = 1/sicro.GetMoistAirVolume(self._T_idb,self._w_i/1000,self.props["ATM_PRESSURE"])

        if self._Q_required > 0: # Heating    
            Q_eq,Q_coil,f_load = self._equipment.get_heating_load(self._T_idb, self._T_iwb, self._T_odb, self._T_owb,self._f_air,self._Q_required)
            if f_load == 1:
                state = 1
            else:
                state = 2
        elif self._Q_required < 0: # Cooling
            Q_eq, Q_coil, Q_lat,f_load = self._equipment.get_cooling_load(self._T_idb, self._T_iwb, self._T_odb,self._T_owb,self._f_air,self._Q_required)
            if f_load == 1:
                state = -2
            else:
                state = -1
            M_w = -(Q_lat) / self.props["LAMBDA"]
            Q_coil = -Q_coil
            Q_eq = -Q_eq

        self._state = state
        self._Q_coil = Q_coil 
        self._Q_eq = Q_eq
        self._M_w = M_w
        self._f_load = f_load

        air_flow = {"M_a": self._air_flow * self._f_oa * self._rho_i, 
                    "T_a": self._T_odb, 
                    "w_a":self._w_o, 
                    "Q_s": Q_eq, 
                    "M_w":self._M_w }
        return air_flow  

    def _mix_air(self, f, T1, w1, T2, w2):
        T = f * T1 + (1-f)*T2
        w = f * w1 + (1-f)*w2
        if (T > 100):
            T_wb = 50 # Inventado
        else:
            T_wb = sicro.GetTWetBulbFromHumRatio(T,w/1000,self.props["ATM_PRESSURE"])
        return (T,w,T_wb)        

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        self.variable("state").values[time_index] = self._state
        if self._state != 0 : # on
            self.variable("T_MA").values[time_index] = self._T_idb
            self.variable("T_MAwb").values[time_index] = self._T_iwb
            m_supply = self._air_flow * self._rho_i
            self.variable("m_air_flow").values[time_index] = m_supply
            self.variable("outdoor_air_fraction").values[time_index] = self._f_oa
            self.variable("T_SA").values[time_index] = self._Q_eq/(m_supply*self.props["C_PA"]) + self._T_idb
            self.variable("w_SA").values[time_index] = self._M_w/(self._air_flow * self._rho_i) +self._w_i
            self.variable("F_air").values[time_index] = self._f_air
            self.variable("F_load").values[time_index] = self._f_load
            if self._state == 1 or self._state == 2: # Heating
                power,fan_power, F_COP = self._equipment.get_heating_power(self._T_idb,self._T_iwb,self._T_odb,self._T_owb,self._f_air,self._Q_required)
                Q_sys = self._Q_coil
                self.variable("Q_sensible").values[time_index] = Q_sys
                self.variable("Q_total").values[time_index] = Q_sys
                self.variable("power").values[time_index] = power
                self.variable("indoor_fan_power").values[time_index] = fan_power
                if power>0:
                    self.variable("COP").values[time_index] = Q_sys/power
                    self.variable("efficiency_degradation").values[time_index] = F_COP
            elif self._state == -1 or self._state == -2: #Cooling
                power,fan_power,F_EER = self._equipment.get_cooling_power(self._T_idb,self._T_iwb,self._T_odb,self._T_owb,self._f_air,self._Q_required)
                Q_s = -self._Q_coil 
                Q_l = -self._M_w * self.props["LAMBDA"]
                self.variable("Q_sensible").values[time_index] = Q_s
                self.variable("Q_latent").values[time_index] = Q_l
                self.variable("Q_total").values[time_index] = Q_s + Q_l
                self.variable("power").values[time_index] = power
                self.variable("indoor_fan_power").values[time_index] = fan_power
                if power>0: 
                    self.variable("EER").values[time_index] = (Q_s+Q_l)/power
                    self.variable("efficiency_degradation").values[time_index] = F_EER
            else: # venting
                self.variable("power").values[time_index] = self._equipment.get_fan_power(0)
                self.variable("indoor_fan_power").values[time_index] = self._equipment.get_fan_power(0)
