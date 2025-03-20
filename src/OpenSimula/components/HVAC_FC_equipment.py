from OpenSimula.Iterative_process import Iterative_process
from OpenSimula.Message import Message
from OpenSimula.Parameters import Parameter_float, Parameter_float_list, Parameter_math_exp, Parameter_options, Parameter_boolean
from OpenSimula.Component import Component
from OpenSimula.components.utils.fluid_props import rhocp_water
from scipy.optimize import fsolve
import psychrolib as sicro

class HVAC_FC_equipment(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_FC_equipment"
        self.parameter("description").value = "HVAC Fan-coil equipment manufacturer information"
        self.add_parameter(Parameter_float("nominal_air_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("nominal_cooling_water_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("nominal_total_cooling_capacity", 0, "W", min=0))
        self.add_parameter(Parameter_float("nominal_sensible_cooling_capacity", 0, "W", min=0))
        self.add_parameter(Parameter_float("fan_power", 0, "W", min=0))
        self.add_parameter(Parameter_float_list("nominal_cooling_conditions", [27, 19, 7], "ºC"))
        self.add_parameter(Parameter_float("nominal_heating_water_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("nominal_heating_capacity", 0, "W", min=0))
        self.add_parameter(Parameter_float_list("nominal_heating_conditions", [20, 15, 50], "ºC"))
        self.add_parameter(Parameter_options("fan_operation", "CONTINUOUS", ["CONTINUOUS", "CYCLING"]))
        self.add_parameter(Parameter_math_exp("heating_epsilon_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("cooling_epsilon_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("cooling_adp_epsilon_expression", "1", "frac"))
        self.add_parameter(Parameter_float_list("expression_max_values", [60,30,99,2,2,1], "-"))
        self.add_parameter(Parameter_float_list("expression_min_values", [-30,-30,0,0,0,0], "-"))

        # Sicro
        sicro.SetUnitSystem(sicro.SI)
        self.CP_A = 1007 # (J/kg·K)
        self.DH_W = 2501 # (J/g H20)


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
        # Pressure and RHO_A
        self._file_met = self.project().parameter("simulation_file_met").component
        self.ATM_PRESSURE = sicro.GetStandardAtmPressure(self._file_met.altitude)
        self.RHO_A = sicro.GetMoistAirDensity(20,0.0073,self.ATM_PRESSURE)

        # Parameters
        self._nominal_air_flow = self.parameter("nominal_air_flow").value
        self._fan_power = self.parameter("fan_power").value
        # Heating
        self._nominal_heating_capacity = self.parameter("nominal_heating_capacity").value
        self._nominal_heating_water_flow = self.parameter("nominal_heating_water_flow").value
        self._T_idb_HN = self.parameter("nominal_heating_conditions").value[0]
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
            C_min = min(self._nominal_air_flow*self.RHO_A*self.CP_A, self._nominal_heating_water_flow*rhocp_water(self._T_iw_HN))
            Q_max = C_min * (self._T_iw_HN - self._T_idb_HN)
            self._nominal_heating_epsilon = self._nominal_heating_capacity/Q_max
            if self._nominal_heating_epsilon > 1:
                self._sim_.message(Message(f"{self.parameter('name').value} : Nominal heating effectiveness > 1","ERROR"))
        else:
            self._nominal_heating_epsilon = 0
        
        # Cooling
        if self._nominal_total_cooling_capacity > 0:
            T_ri =sicro.GetTDewPointFromTWetBulb(self._T_idb_CN,self._T_iwb_CN,self.ATM_PRESSURE)
            if T_ri < self._T_iw_CN:
                self._sim_.message(Message(f"{self.parameter('name').value} : Nominal dry coil, inlet water temperature must be less than inlet dew point temperature","ERROR"))
            w_i = sicro.GetHumRatioFromTWetBulb(self._T_idb_CN,self._T_iwb_CN,self.ATM_PRESSURE)
            h_ia = sicro.GetMoistAirEnthalpy(self._T_idb_CN,w_i)
            h_iw = sicro.GetMoistAirEnthalpy(self._T_iw_CN,sicro.GetHumRatioFromRelHum(self._T_iw_CN,1,self.ATM_PRESSURE))
            self._nominal_enthalpy_epsilon = self._nominal_total_cooling_capacity / (self._nominal_air_flow*self.RHO_A*(h_ia-h_iw))
            if (self._nominal_enthalpy_epsilon > 1):
                self._sim_.message(Message(f"{self.parameter('name').value} : Nominal cooling effectiveness > 1","ERROR"))
            h_oa = h_ia - self._nominal_total_cooling_capacity/(self._nominal_air_flow*self.RHO_A)
            T_odb = self._T_idb_CN - self._nominal_sensible_cooling_capacity/(self._nominal_air_flow*self.RHO_A*self.CP_A)
            w_o = sicro.GetHumRatioFromEnthalpyAndTDryBulb(h_oa,T_odb)
            # Calculate ADP
            self._nominal_T_adp = self.calculate_ADP(self._T_idb_CN,w_i,T_odb,w_o)
            self._nominal_cooling_adp_epsilon = (self._T_idb_CN - T_odb)/(self._T_idb_CN - self._nominal_T_adp)
            if (self._nominal_cooling_adp_epsilon > 1):
                self._sim_.message(Message(f"{self.parameter('name').value} : Nominal cooling ADP effectiveness > 1","ERROR"))
        else:
            self._nominal_enthalpy_epsilon = 0
            self._nominal_cooling_adp_epsilon = 0

    def calculate_ADP(self,T_i,w_i,T_o,w_o):
        def func(x):
            w_adp = sicro.GetHumRatioFromRelHum(x,1,self.ATM_PRESSURE)
            w_adp2 = w_i - (T_i -x) * (w_i - w_o)/(T_i-T_o)
            return w_adp - w_adp2
        solucion = fsolve(func, x0=T_o -1,xtol=1e-3)
        return solucion[0]      

    def get_heating_state(self,T_idb,T_iwb,T_iw,F_air,F_water,F_load):
        """
        Returns (Q,epsilon,fan_power). 
        If fan_operation is CONTINUOUS: It returns the values from the expressions (Gross capacity = Coil capacity)
        If fan_operation is CYCLING: It returns the expressions plus the indoor fan power (Net capacity = Gross capacity + indoor fan)  """
       
        if self._nominal_heating_capacity > 0:
            # variables dictonary
            var_dic = self._var_state_dic([T_idb, T_iwb,T_iw,F_air,F_water,F_load])
            # Capacity
            epsilon = self._nominal_heating_epsilon * self.parameter("heating_epsilon_expression").evaluate(var_dic)
            C_min = min(self._nominal_air_flow*F_air*self.RHO_A*self.CP_A, self._nominal_heating_water_flow*F_water*rhocp_water(T_iw))
            capacity = epsilon * C_min * (T_iw - T_idb)
            if self.parameter("fan_operation").value == "CYCLING":
                capacity = capacity + self.parameter("fan_power").value
                return (capacity*F_load, epsilon,self._fan_power*F_load)
            elif self.parameter("fan_operation").value == "CONTINUOUS":
                return (capacity*F_load, epsilon, self._fan_power)
        else:
            return (0,0,0)


    def get_cooling_state(self,T_idb,T_iwb,T_iw,F_air, F_water,F_load):
        """
        Returns (Q_tot,Q_sen,ent_epsilon,adp_epsilon,fan_power). 
        If fan_operation is CONTINUOUS: It returns the values from the expressions (Gross capacity = Coil capacity)
        If fan_operation is CYCLING: It returns the expressions minus the indoor fan power (Net capacity = Gross capacity - indoor fan)  
        """
        if self._nominal_total_cooling_capacity > 0:
            T_ri =sicro.GetTDewPointFromTWetBulb(T_idb,T_iwb,self.ATM_PRESSURE)
            w_i = sicro.GetHumRatioFromTWetBulb(T_idb,T_iwb,self.ATM_PRESSURE)
            h_ia = sicro.GetMoistAirEnthalpy(T_idb,w_i)
            # variables dictonary
            var_dic = self._var_state_dic([T_idb, T_iwb,T_iw,F_air, F_water,F_load])
            # epsilon
            epsilon = self._nominal_enthalpy_epsilon * self.parameter("cooling_epsilon_expression").evaluate(var_dic)
            adp_epsilon = self._nominal_cooling_adp_epsilon * self.parameter("cooling_adp_epsilon_expression").evaluate(var_dic)
            if T_ri < T_iw: # Dry coil
                h_iw = sicro.GetMoistAirEnthalpy(T_iw,w_i)
                Q_tot = epsilon * self._nominal_air_flow*self.RHO_A * (h_ia - h_iw)
                Q_sen = Q_tot
            else:  # Wet coil
                h_iw = sicro.GetMoistAirEnthalpy(T_iw,sicro.GetHumRatioFromRelHum(T_iw,1,self.ATM_PRESSURE))
                Q_tot = epsilon * self._nominal_air_flow*self.RHO_A * (h_ia - h_iw)
                h_oa = h_ia - Q_tot/(self._nominal_air_flow*self.RHO_A)
                h_adp = h_ia - (h_ia -h_oa)/adp_epsilon
                T_adp = self.get_T_adp_from_h_adp(h_adp,T_iw + 4)
                Q_sen = self._nominal_air_flow*self.RHO_A*self.CP_A*(T_idb-T_adp)*adp_epsilon
                if (Q_sen > Q_tot):
                    Q_sen = Q_tot
            if self.parameter("fan_operation").value == "CYCLING":
                Q_tot = Q_tot - self.parameter("fan_power").value
                Q_sen = Q_sen - self.parameter("fan_power").value
                return (Q_tot*F_load,Q_sen*F_load,epsilon,adp_epsilon,self._fan_power*F_load)
            elif self.parameter("fan_operation").value == "CONTINUOUS":
                return (Q_tot*F_load,Q_sen*F_load,epsilon,adp_epsilon,self._fan_power)
        else:
            return (0,0,0,0,0)
    
    def get_T_adp_from_h_adp(self,h_adp,T_ini):
        def func(x):
            return (h_adp - sicro.GetSatAirEnthalpy(x,self.ATM_PRESSURE))
        solucion = fsolve(func, x0=T_ini,xtol=1e-3)
        return solucion[0]      
        
    def get_no_load_power(self):
        if self.parameter("fan_operation").value == "CONTINUOUS":
            return self.parameter("fan_power").value
        elif self.parameter("fan_operation").value == "CYCLING":
            return 0
    
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
                "F_water":values[4],
                "F_load":values[5]}




        