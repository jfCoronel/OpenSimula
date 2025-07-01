from OpenSimula.Iterative_process import Iterative_process
from OpenSimula.Message import Message
from OpenSimula.Parameters import Parameter_component, Parameter_float, Parameter_variable_list, Parameter_math_exp, Parameter_options
from OpenSimula.Component import Component
from OpenSimula.Variable import Variable
import psychrolib as sicro

class HVAC_SZW_system(Component): # HVAC Single Zone Water system
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_SZW_system"
        self.parameter("description").value = "HVAC Single Zone Water system"
        self.add_parameter(Parameter_component("space", "not_defined", ["Space"])) # Space
        self.add_parameter(Parameter_component("coil", "not_defined", ["HVAC_coil_equipment"]))
        self.add_parameter(Parameter_component("supply_fan", "not_defined", ["HVAC_fan_equipment"]))
        self.add_parameter(Parameter_component("return_fan", "not_defined", ["HVAC_fan_equipment"]))
        self.add_parameter(Parameter_float("air_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("return_air_flow", 1, "m³/s", min=0)) # Not used when return fan is not defined
        self.add_parameter(Parameter_math_exp("outdoor_air_fraction", "0", "frac"))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("heating_setpoint", "20", "°C"))
        self.add_parameter(Parameter_math_exp("cooling_setpoint", "25", "°C"))
        self.add_parameter(Parameter_math_exp("system_on_off", "1", "on/off"))
        self.add_parameter(Parameter_options("fan_operation", "CONTINUOUS", ["CONTINUOUS", "CYCLING"]))
        self.add_parameter(Parameter_options("water_source", "UNKNOWN", ["UNKNOWN", "WATER_LOOP"]))
        self.add_parameter(Parameter_float("cooling_water_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("heating_water_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("inlet_cooling_water_temp", 7, "ºC"))
        self.add_parameter(Parameter_float("inlet_heating_water_temp", 50, "ºC"))
        self.add_parameter(Parameter_options("water_flow_control", "ON_OFF", ["ON_OFF", "PROPORTIONAL"]))
        self.add_parameter(Parameter_options("economizer", "NO", ["NO", "TEMPERATURE","TEMPERATURE_NOT_INTEGRATED","ENTHALPY","ENTHALPY_LIMITED"]))
        self.add_parameter(Parameter_float("economizer_DT", 0, "ºC", min=0))
        self.add_parameter(Parameter_float("economizer_enthalpy_limit", 0, "kJ/kg", min=0))

        # Variables
        self.add_variable(Variable("state", unit="flag")) # 0: 0ff, 1: Heating, 2: Heating max cap, -1:Cooling, -2:Cooling max cap, 3: Venting 
        self.add_variable(Variable("T_odb", unit="°C"))
        self.add_variable(Variable("T_owb", unit="°C"))
        self.add_variable(Variable("T_idb", unit="°C"))
        self.add_variable(Variable("T_iwb", unit="°C"))
        self.add_variable(Variable("F_load", unit="frac"))
        self.add_variable(Variable("outdoor_air_fraction", unit="frac"))
        self.add_variable(Variable("m_air_flow", unit="kg/s"))
        self.add_variable(Variable("T_supply", unit="°C"))
        self.add_variable(Variable("w_supply", unit="g/kg"))
        self.add_variable(Variable("T_fan_in", unit="°C"))
        self.add_variable(Variable("w_fan_in", unit="g/kg"))
        self.add_variable(Variable("Q_sensible", unit="W"))
        self.add_variable(Variable("Q_latent", unit="W"))
        self.add_variable(Variable("Q_total", unit="W"))
        self.add_variable(Variable("supply_fan_power", unit="W"))
        self.add_variable(Variable("return_fan_power", unit="W"))
        self.add_variable(Variable("heating_setpoint", unit="°C"))
        self.add_variable(Variable("cooling_setpoint", unit="°C"))
        self.add_variable(Variable("epsilon", unit="frac"))
        self.add_variable(Variable("epsilon_adp", unit="frac"))
        self.add_variable(Variable("T_iw", unit="°C"))
        self.add_variable(Variable("T_ow", unit="°C"))
        self.add_variable(Variable("T_adp", unit="°C"))
        self.add_variable(Variable("T_return", unit="°C")) # Return air temperature
    def check(self):
        errors = super().check()
        # Test space defined
        if self.parameter("space").value == "not_defined":
            msg = f"{self.parameter('name').value}, must define its space."
            errors.append(Message(msg, "ERROR"))
        # Test coil defined
        if self.parameter("coil").value == "not_defined":
            msg = f"{self.parameter('name').value}, must define its coil equipment."
            errors.append(Message(msg, "ERROR"))
        # Test supply fan defined
        if self.parameter("supply_fan").value == "not_defined":
            msg = f"{self.parameter('name').value}, must define its supply fan equipment."
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
        self._coil = self.parameter("coil").component
        self._supply_fan = self.parameter("supply_fan").component
        self._return_fan = self.parameter("return_fan").component
        self._air_flow = self.parameter("air_flow").value
        self._return_air_flow = self.parameter("return_air_flow").value

        # Water flows and temperatures
        self._cooling_water_flow = self.parameter("cooling_water_flow").value
        self._heating_water_flow = self.parameter("heating_water_flow").value
        self._cooling_F_water = self._cooling_water_flow/self._coil.parameter("nominal_cooling_water_flow").value
        self._heating_F_water = self._heating_water_flow/self._coil.parameter("nominal_heating_water_flow").value
        self._cooling_water_temp = self.parameter("inlet_cooling_water_temp").value
        self._heating_water_temp = self.parameter("inlet_heating_water_temp").value
        self._rho_i = self.props["RHO_A"] 
        # Fan operation
        self._fan_operation = self.parameter("fan_operation").value
        self._fans_heat = self._get_fan_power("supply", 0) + self._get_fan_power("return", 0)
        # adp model
        self._water_flow_control = self.parameter("water_flow_control").value
        
    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        # Outdoor air
        self._T_odb = self._file_met.variable("temperature").values[time_index]
        self._T_owb = self._file_met.variable("wet_bulb_temp").values[time_index]
        self._w_o = self._file_met.variable("abs_humidity").values[time_index]
        self.variable("T_odb").values[time_index] = self._T_odb
        self.variable("T_owb").values[time_index] = self._T_owb 
        self._outdoor_rho = 1/sicro.GetMoistAirVolume(self._T_odb,self._w_o/1000,self.props["ATM_PRESSURE"])

        # variables dictonary
        var_dic = self.get_parameter_variable_dictionary(time_index)
        # outdoor air fraction 
        self._f_oa_min = self.parameter("outdoor_air_fraction").evaluate(var_dic)
        self._f_oa = self._f_oa_min
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
        # Starting with the system venting
        self._f_load = 0

    
    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)
        space_air = {"M_a": 0, "T_a": 0, "w_a":0, "Q_s":0, "M_w":0 }
        if self._on_off:
            self._T_space = self._space.variable("temperature").values[time_index]
            self._w_space = self._space.variable("abs_humidity").values[time_index]
            self._calculate_return_air_temperature()
            # Calculate Q_required
            self._calculate_required_Q()
            if (self.parameter("economizer").value != "NO"):
                self._simulate_economizer() # Calculation of new f_oa
                self._calculate_required_Q()
            space_air = self._simulate_system()            
        self._space.set_control_system(space_air)
        return True

    def _calculate_required_Q(self):
        K_t,F_t = self._space.get_thermal_equation(False)
        m_cp_oa = self._air_flow * self._f_oa * self._rho_i * self.props["C_PA"]
        K_ts = K_t + m_cp_oa
        F_ts = F_t + m_cp_oa * self._T_odb + self._fans_heat
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
    
    def _get_fan_power(self, fan, f_load):
        if fan == "supply":
            if self._fan_operation == "CONTINUOUS":
                return self._supply_fan.get_power(self._air_flow)
            elif self._fan_operation == "CYCLING":
                return self._supply_fan.get_power(self._air_flow)*f_load
        elif fan == "return":
            if self._return_fan is None: # No return fan
                return 0
            else:
                if self._fan_operation == "CONTINUOUS":
                    return self._return_fan.get_power(self._return_air_flow)
                elif self._fan_operation == "CYCLING":
                    return self._return_fan.get_power(self._return_air_flow)*f_load
    
    def _calculate_return_air_temperature(self):
        # Return fan
        Q_return_fan = self._get_fan_power("return",self._f_load)
        self._T_return =self._T_space
        if Q_return_fan > 0:
            m_return = self._air_flow * (1-self._f_oa_min) * self._rho_i
            if m_return > 0:
                self._T_return = Q_return_fan/(m_return*self.props["C_PA"]) + self._T_space


    def _calculate_mixed_air(self):
        # Mixed air
        self._T_idb, self._w_i, self._T_iwb = self._mix_air(self._f_oa, self._T_odb, self._w_o, self._T_return, self._w_space)
        self._rho_i = 1/sicro.GetMoistAirVolume(self._T_idb,self._w_i/1000,self.props["ATM_PRESSURE"])        

    def _simulate_economizer(self): 
        if (self.parameter("economizer").value == "TEMPERATURE" or self.parameter("economizer").value == "TEMPERATURE_NOT_INTEGRATED"):
            on_economizer = self._T_odb < self._T_return-self.parameter("economizer_DT").value
        elif (self.parameter("economizer").value == "ENTHALPY"):
            h_odb = sicro.GetMoistAirEnthalpy(self._T_odb,self._w_o/1000)
            h_return = sicro.GetMoistAirEnthalpy(self._T_return,self._w_space/1000)
            on_economizer = h_odb < h_return
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
                        self._f_oa = self._f_oa_min
                    else:
                        self._f_oa = 1
            elif (self._Q_required > 0): # Heating 
                self._f_oa = self._f_oa_min
        else:
            self._f_oa = self._f_oa_min

    def _simulate_system(self):
        self._calculate_mixed_air()
        if self._Q_required > 0: # Heating    
            self._simulate_heating()
        elif self._Q_required < 0: # Cooling
             self._simulate_cooling()
        else:   # Venting
            self._state = 3
            self._f_load = 0
            self._Q_coil = 0
            self._Q_eq = self._fans_heat
            self._M_w = 0

        air_flow = {"M_a": self._air_flow * self._f_oa * self._rho_i, 
                    "T_a": self._T_odb, 
                    "w_a": self._w_o, 
                    "Q_s": self._Q_eq, 
                    "M_w": self._M_w }
        return air_flow          

    def _simulate_heating(self):
        capacity = self._coil.get_heating_capacity(self._T_idb, self._T_iwb, self._heating_water_temp,self._air_flow,self._heating_water_flow)
        self._M_w = 0 # No latent load in heating
        if self._fans_heat > 0: # Q_required is only the coil capacity
            if capacity < self._Q_required: # Coil capacity is not enough
                self._Q_coil = capacity
                self._Q_eq = self._fans_heat + capacity
                self._f_load = 1
                self._state = 2
            else:
                self._Q_coil = self._Q_required
                self._f_load = self._Q_coil / capacity
                self._Q_eq = self._Q_required + self._get_fan_power("supply", self._f_load) + self._get_fan_power("return", self._f_load)
                self._state = 1
        else: # Fans heat is not considered, Q_required is equipment capacity
            capacity_eq = capacity + self._get_fan_power("supply", 1) + self._get_fan_power("return", 1)
            if capacity_eq < self._Q_required:
                self._Q_eq = capacity_eq
                self._Q_coil = capacity
                self._f_load = 1
                self._state = 2
            else:
                self._state = 1
                self._Q_eq = self._Q_required
                self._f_load = self._Q_eq / capacity_eq
                self._Q_coil = self._Q_required - self._get_fan_power("supply", self._f_load) - self._get_fan_power("return", self._f_load)


    def _simulate_cooling(self):
        capacity_sen, capacity_lat, self._T_adp = self._coil.get_cooling_capacity(self._T_idb, self._T_iwb,self._cooling_water_temp,self._air_flow,self._cooling_water_flow)
        Q_required = -self._Q_required
        if self._fans_heat > 0: # Q_required is only the coil capacity
            if capacity_sen < Q_required: # Coil capacity is not enough
                self._Q_coil = - capacity_sen
                self._Q_eq = self._fans_heat - capacity_sen
                self._M_w = - (capacity_lat) / self.props["LAMBDA"]
                self._f_load = 1
                self._state = -2
            else:
                self._Q_coil = - Q_required
                self._f_load = Q_required / capacity_sen
                self._Q_eq = - Q_required + self._get_fan_power("supply", self._f_load) + self._get_fan_power("return", self._f_load)
                if self._water_flow_control == "ON_OFF":
                    self._M_w = - (capacity_lat*self._f_load) / self.props["LAMBDA"]
                elif self._water_flow_control == "PROPORTIONAL":
                    mrhocp = self._air_flow * self._rho_i * self.props["C_PA"]
                    T_odb = self._T_idb - (Q_required) / mrhocp
                    Q_lat, self._T_adp = self._coil.get_latent_cooling_load(self._T_idb, self._T_iwb, self._cooling_water_temp, self._air_flow, self._cooling_water_flow, T_odb)
                    self._M_w = - Q_lat / self.props["LAMBDA"]
                self._state = -1
        else: # Fans heat is not considered, Q_required is equipment capacity
            capacity_eq = capacity_sen - self._get_fan_power("supply", 1) - self._get_fan_power("return", 1)
            if capacity_eq < self._Q_required:
                self._Q_eq = -capacity_eq
                self._Q_coil = -capacity_sen
                self._M_w = - (capacity_lat) / self.props["LAMBDA"]
                self._f_load = 1
                self._state = -2
            else:
                self._state = -1
                self._Q_eq = -Q_required
                self._f_load = Q_required / capacity_eq
                self._Q_coil = -Q_required - self._get_fan_power("supply", self._f_load) - self._get_fan_power("return", self._f_load)
                if self._water_flow_control == "ON_OFF":
                    self._M_w = - (capacity_lat*self._f_load) / self.props["LAMBDA"]
                elif self._water_flow_control == "PROPORTIONAL":
                    mrhocp = self._nominal_air_flow * self._rho_i * self.props["C_PA"]
                    T_odb = self._T_idb + (self._Q_coil) / mrhocp
                    Q_lat, self._T_adp = self._coil.get_latent_cooling_load(self._T_idb, self._T_iwb, self._cooling_water_temp, self._air_flow, self._cooling_water_flow, T_odb)
                    self._M_w = - Q_lat / self.props["LAMBDA"]    
                

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        self.variable("state").values[time_index] = self._state
        if self._state != 0 : # on
            self.variable("T_idb").values[time_index] = self._T_idb
            self.variable("T_iwb").values[time_index] = self._T_iwb
            m_supply = self._air_flow * self._rho_i
            self.variable("m_air_flow").values[time_index] = m_supply
            self.variable("outdoor_air_fraction").values[time_index] = self._f_oa
            # Density of air at the fan inlet
            T_fan_in = self._Q_coil/(m_supply*self.props["C_PA"]) + self._T_idb
            w_fan_in = self._M_w/m_supply +self._w_i
            self.variable("T_fan_in").values[time_index] = T_fan_in
            self.variable("w_fan_in").values[time_index] = w_fan_in
            self.variable("T_supply").values[time_index] = self._get_fan_power("supply",self._f_load)/(m_supply*self.props["C_PA"]) + T_fan_in
            self.variable("w_supply").values[time_index] = w_fan_in
            self.variable("T_return").values[time_index] =self._T_return
            self.variable("F_load").values[time_index] = self._f_load
            self.variable("supply_fan_power").values[time_index] = self._get_fan_power("supply", self._f_load)
            self.variable("return_fan_power").values[time_index] = self._get_fan_power("return", self._f_load)          
            if self._state == 1 or self._state == 2: # Heating
                Q_sys = self._Q_coil
                self.variable("Q_sensible").values[time_index] = Q_sys
                self.variable("Q_total").values[time_index] = Q_sys
                self.variable("T_iw").values[time_index] = self._heating_water_temp
                self.variable("T_ow").values[time_index] = self._heating_water_temp - Q_sys/(self._heating_water_flow * self.props["RHOCP_W"](self._heating_water_temp))                    
                self.variable("T_adp").values[time_index] = 0
            elif self._state == -1 or self._state == -2: #Cooling
                Q_s = -self._Q_coil
                Q_l = -self._M_w * self.props["LAMBDA"]
                self.variable("Q_sensible").values[time_index] = Q_s
                self.variable("Q_latent").values[time_index] = Q_l
                self.variable("Q_total").values[time_index] = Q_s
                self.variable("T_iw").values[time_index] = self._cooling_water_temp
                self.variable("T_ow").values[time_index] = self._cooling_water_temp + (Q_s+Q_l)/(self._cooling_water_flow * self.props["RHOCP_W"](self._cooling_water_temp))                
                self.variable("T_adp").values[time_index] = self._T_adp              
