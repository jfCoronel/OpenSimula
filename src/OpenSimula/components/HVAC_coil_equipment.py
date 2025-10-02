from opensimula.Message import Message
from opensimula.Parameters import Parameter_float, Parameter_float_list, Parameter_math_exp, Parameter_options, Parameter_boolean
from opensimula.Component import Component
from scipy.optimize import fsolve
import psychrolib as sicro

class HVAC_coil_equipment(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_coil_equipment"
        self.parameter("description").value = "HVAC coil equipment manufacturer information"
        self.add_parameter(Parameter_float("nominal_air_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("nominal_cooling_water_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("nominal_total_cooling_capacity", 0, "W", min=0))
        self.add_parameter(Parameter_float("nominal_sensible_cooling_capacity", 0, "W", min=0))
        self.add_parameter(Parameter_float_list("nominal_cooling_conditions", [27, 19, 7], "ºC"))
        self.add_parameter(Parameter_float("nominal_heating_water_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("nominal_heating_capacity", 0, "W", min=0))
        self.add_parameter(Parameter_float_list("nominal_heating_conditions", [20, 15, 50], "ºC"))
        self.add_parameter(Parameter_math_exp("heating_epsilon_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("cooling_epsilon_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("cooling_adp_epsilon_expression", "1", "frac"))
        self.add_parameter(Parameter_float_list("expression_max_values", [60,30,99,2,2], "-"))
        self.add_parameter(Parameter_float_list("expression_min_values", [-30,-30,0,0,0], "-"))

    def check(self):
        errors = super().check()
        # Test Cooling and Heating conditions: 3, 3 values (Entering air and water)
        if len(self.parameter("nominal_cooling_conditions").value)!= 3:
            msg = f"{self.parameter('name').value}, nominal_cooling_conditions size must be 3"
            errors.append(Message(msg, "ERROR"))
        if len(self.parameter("nominal_heating_conditions").value)!= 3:
            msg = f"{self.parameter('name').value}, nominal_heating_conditions size must be 3"
            errors.append(Message(msg, "ERROR"))
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        # Sicro
        sicro.SetUnitSystem(sicro.SI)
        self.props = self._sim_.props

        # Parameters
        self._nominal_air_flow = self.parameter("nominal_air_flow").value
        # Heating
        self._nominal_heating_capacity = self.parameter("nominal_heating_capacity").value
        self._nominal_heating_water_flow = self.parameter("nominal_heating_water_flow").value
        self._T_idb_HN = self.parameter("nominal_heating_conditions").value[0]
        self._T_iwb_HN = self.parameter("nominal_heating_conditions").value[1]
        self._T_iw_HN = self.parameter("nominal_heating_conditions").value[2]
        # Cooling
        self._nominal_total_cooling_capacity = self.parameter("nominal_total_cooling_capacity").value
        self._nominal_sensible_cooling_capacity = self.parameter("nominal_sensible_cooling_capacity").value
        self._nominal_cooling_water_flow = self.parameter("nominal_cooling_water_flow").value
        self._T_idb_CN = self.parameter("nominal_cooling_conditions").value[0]
        self._T_iwb_CN = self.parameter("nominal_cooling_conditions").value[1]
        self._T_iw_CN = self.parameter("nominal_cooling_conditions").value[2]

        self.calculate_nominal_effectiveness()
    
    def calculate_nominal_effectiveness(self):
        # Heating
        if self._nominal_heating_capacity > 0:
            w = sicro.GetHumRatioFromTWetBulb(self._T_iw_HN,self._T_iwb_HN,101325)
            rho = 1/sicro.GetMoistAirVolume(self._T_idb_HN,w,101325)
            C_min = min( self._nominal_air_flow * rho * self.props["C_PA"], self._nominal_heating_water_flow * self.props["RHOCP_W"](self._T_iw_HN))
            Q_max = C_min * (self._T_iw_HN - self._T_idb_HN)
            self._nominal_heating_epsilon = self._nominal_heating_capacity/Q_max
            if self._nominal_heating_epsilon > 1:
                self._sim_.message(Message(f"{self.parameter('name').value} : Nominal heating effectiveness > 1","ERROR"))
        else:
            self._nominal_heating_epsilon = 0
        
        # Cooling
        if self._nominal_total_cooling_capacity > 0:
            T_ri =sicro.GetTDewPointFromTWetBulb(self._T_idb_CN,self._T_iwb_CN,101325)
            if T_ri < self._T_iw_CN:
                self._sim_.message(Message(f"{self.parameter('name').value} : Nominal dry coil, inlet water temperature must be less than inlet dew point temperature","ERROR"))
            w_i = sicro.GetHumRatioFromTWetBulb(self._T_idb_CN,self._T_iwb_CN,101325)
            rho = 1/sicro.GetMoistAirVolume(self._T_idb_CN,w_i,101325)
            h_ia = sicro.GetMoistAirEnthalpy(self._T_idb_CN,w_i)
            h_iw = sicro.GetMoistAirEnthalpy(self._T_iw_CN,sicro.GetHumRatioFromRelHum(self._T_iw_CN,1,101325))
            self._nominal_enthalpy_epsilon = self._nominal_total_cooling_capacity / (self._nominal_air_flow * rho * (h_ia-h_iw))
            if (self._nominal_enthalpy_epsilon > 1):
                self._sim_.message(Message(f"{self.parameter('name').value} : Nominal cooling effectiveness > 1","ERROR"))
            h_oa = h_ia - self._nominal_total_cooling_capacity/(self._nominal_air_flow * rho)
            T_odb = self._T_idb_CN - self._nominal_sensible_cooling_capacity/(self._nominal_air_flow * rho * self.props["C_PA"])
            w_o = sicro.GetHumRatioFromEnthalpyAndTDryBulb(h_oa,T_odb)
            # Calculate ADP
            self._nominal_T_adp = self.calculate_ADP(self._T_idb_CN,w_i,T_odb,w_o,101325)
            self._nominal_cooling_adp_epsilon = (self._T_idb_CN - T_odb)/(self._T_idb_CN - self._nominal_T_adp)
            if (self._nominal_cooling_adp_epsilon > 1):
                self._sim_.message(Message(f"{self.parameter('name').value} : Nominal cooling ADP effectiveness > 1","ERROR"))
        else:
            self._nominal_enthalpy_epsilon = 0
            self._nominal_cooling_adp_epsilon = 0

    def calculate_ADP(self,T_i,w_i,T_o,w_o,p):
        def func(x):
            w_adp = sicro.GetHumRatioFromRelHum(x,1,p)
            w_adp2 = w_i - (T_i -x) * (w_i - w_o)/(T_i-T_o)
            return w_adp - w_adp2
        solucion = fsolve(func, x0=T_o -1,xtol=1e-3)
        return solucion[0]      

    def get_heating_capacity(self,T_idb,T_iwb,T_iw,air_flow,water_flow):
        if self._nominal_heating_capacity > 0:
            # variables dictonary
            F_air = air_flow/ self._nominal_air_flow
            F_water = water_flow/ self._nominal_heating_water_flow
            var_dic = self._var_state_dic([T_idb, T_iwb,T_iw,F_air,F_water])
            w_i = sicro.GetHumRatioFromTWetBulb(T_idb,T_iwb,self.props["ATM_PRESSURE"])
            rho_i = 1/sicro.GetMoistAirVolume(T_idb,w_i,self.props["ATM_PRESSURE"])

            # Capacity
            epsilon = self._nominal_heating_epsilon * self.parameter("heating_epsilon_expression").evaluate(var_dic)
            C_min = min(self._nominal_air_flow * F_air * rho_i * self.props["C_PA"], self._nominal_heating_water_flow*F_water*self.props["RHOCP_W"](T_iw))
            capacity = epsilon * C_min * (T_iw - T_idb)
            return capacity, epsilon
        else:
            return 0, 0

    def get_cooling_capacity(self,T_idb,T_iwb,T_iw,air_flow,water_flow):
        Q_sen = 0
        Q_lat = 0
        T_adp = 0
        epsilon = 0
        adp_epsilon = 0
        if self._nominal_total_cooling_capacity > 0:
            # variables dictonary
            F_air = air_flow/ self._nominal_air_flow
            F_water = water_flow/ self._nominal_cooling_water_flow
            var_dic = self._var_state_dic([T_idb, T_iwb,T_iw,F_air, F_water])
            # epsilon
            epsilon = self._nominal_enthalpy_epsilon * self.parameter("cooling_epsilon_expression").evaluate(var_dic)
            adp_epsilon = self._nominal_cooling_adp_epsilon * self.parameter("cooling_adp_epsilon_expression").evaluate(var_dic)
            T_idp =sicro.GetTDewPointFromTWetBulb(T_idb,T_iwb,self.props["ATM_PRESSURE"])
            w_i = sicro.GetHumRatioFromTWetBulb(T_idb,T_iwb,self.props["ATM_PRESSURE"])
            h_i = sicro.GetMoistAirEnthalpy(T_idb,w_i)
            rho_i = 1/sicro.GetMoistAirVolume(T_idb,w_i,self.props["ATM_PRESSURE"])
            mrho = self._nominal_air_flow * F_air * rho_i
            mrhocp = mrho * self.props["C_PA"]  
            if T_idp < T_iw: # Dry coil
                Q_lat = 0
                Q_sen = epsilon * mrhocp * (T_idb - T_iw)
                T_adp = T_idp
            else:  # Wet coil
                h_iw = sicro.GetMoistAirEnthalpy(T_iw,sicro.GetHumRatioFromRelHum(T_iw,1,self.props["ATM_PRESSURE"]))
                Q_tot = epsilon * mrho * (h_i - h_iw)
                h_o = h_i - Q_tot/mrho
                h_adp = h_i - (h_i -h_o)/adp_epsilon
                T_adp = self.get_T_adp_from_h_adp(h_adp,T_iw + 4)
                Q_sen = adp_epsilon * mrhocp * (T_idb - T_adp) 
                if (Q_sen > Q_tot):
                    Q_sen = Q_tot
                Q_lat = Q_tot - Q_sen                                
        return Q_sen, Q_lat, T_adp, epsilon, adp_epsilon
        
    def get_latent_cooling_load(self,T_idb,T_iwb,T_iw,air_flow,water_flow,T_odb):
        # variables dictonary
        F_air = air_flow/ self._nominal_air_flow
        F_water = water_flow/ self._nominal_cooling_water_flow
        var_dic = self._var_state_dic([T_idb, T_iwb,T_iw,F_air, F_water])
        # epsilon
        adp_epsilon = self._nominal_cooling_adp_epsilon * self.parameter("cooling_adp_epsilon_expression").evaluate(var_dic)
        T_adp = T_idb - (T_idb - T_odb)/ adp_epsilon
        T_idp =sicro.GetTDewPointFromTWetBulb(T_idb,T_iwb,self.props["ATM_PRESSURE"])
        w_i = sicro.GetHumRatioFromTWetBulb(T_idb,T_iwb,self.props["ATM_PRESSURE"])
        h_i = sicro.GetMoistAirEnthalpy(T_idb,w_i)
        rho_i = 1/sicro.GetMoistAirVolume(T_idb,w_i,self.props["ATM_PRESSURE"])
        mrho = self._nominal_air_flow * F_air * rho_i
        Q_sen = mrho * self.props["C_PA"] * (T_idb - T_odb)
        if T_adp < T_idp:
            w_adp = sicro.GetHumRatioFromRelHum(T_adp,1,self.props["ATM_PRESSURE"])
            h_adp = sicro.GetMoistAirEnthalpy(T_adp,w_adp)
            cap_tot = adp_epsilon * mrho * (h_i - h_adp)
            Q_lat = cap_tot - Q_sen
        else:
            Q_lat = 0
            T_adp = T_idp
        return Q_lat, T_adp, adp_epsilon

    def get_T_adp_from_h_adp(self,h_adp,T_ini):
        def func(x):
            return (h_adp - sicro.GetSatAirEnthalpy(x,self.props["ATM_PRESSURE"]))
        solucion = fsolve(func, x0=T_ini,xtol=1e-3)
        return solucion[0]      
    
    def _var_state_dic(self, values):
        max = self.parameter("expression_max_values").value
        min = self.parameter("expression_min_values").value
        for i in range(len(values)):
            if (values[i] > max[i]):
                values[i] = max[i]
            elif (values[i] < min[i]):
                values[i] = min[i]
        return {"T_idb":values[0],
                "T_iwb":values[1],
                "T_iw":values[2],
                "F_air":values[3],
                "F_water":values[4]}




        