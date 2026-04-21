from opensimula.Message import Message
from opensimula.Parameters import Parameter_float, Parameter_float_list, Parameter_math_exp, Parameter_options, Parameter_boolean
from opensimula.Component import Component
from scipy.optimize import fsolve

class Chiller(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Chiller"
        self.parameter("description").value = "Chiller equipment manufacturer information"
        self.add_parameter(Parameter_options("chiller_type", "AIR_CONDENSED", ["AIR_CONDENSED", "WATER_CONDENSED"]))
        self.add_parameter(Parameter_float("nominal_water_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("nominal_cooling_capacity", 0, "W", min=0))
        self.add_parameter(Parameter_float("nominal_cooling_power", 0, "W", min=0))
        self.add_parameter(Parameter_float_list("nominal_cooling_conditions", [35, 12, 7], "ºC"))
        self.add_parameter(Parameter_math_exp("cooling_capacity_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("cooling_power_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("EER_expression", "1", "frac"))
        self.add_parameter(Parameter_float("nominal_heating_capacity", 0, "W", min=0))
        self.add_parameter(Parameter_float("nominal_heating_power", 0, "W", min=0))
        self.add_parameter(Parameter_float_list("nominal_heating_conditions", [7, 6, 40, 45], "ºC"))
        self.add_parameter(Parameter_math_exp("heating_capacity_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("heating_power_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("COP_expression", "1", "frac"))
        self.add_parameter(Parameter_float_list("expression_max_values", [80,50,50,1.5,1], "-")) # T_wo, T_ci, T_wbci, F_water, F_load
        self.add_parameter(Parameter_float_list("expression_min_values", [0,-30,-30,0,0], "-")) # T_wo, T_ci, T_wbci, F_water, F_load

    def check(self):
        errors = super().check()
        # Test Cooling and Heating conditions 3 values
        if len(self.parameter("nominal_cooling_conditions").value)!= 3:
            msg = f"Error: {self.parameter('name').value}, nominal_cooling_conditions size must be 3"
            errors.append(Message(msg, "ERROR"))
        if len(self.parameter("nominal_heating_conditions").value)!= 4:
            msg = f"Error: {self.parameter('name').value}, nominal_heating_conditions size must be 4"
            errors.append(Message(msg, "ERROR"))
        return errors
        
    def get_heating_load(self,T_wo,T_ci,T_wbci,F_water,Q_required):
        """
        Q_required: Required heating load
        Returns (Q_eq,f_load).
        Q_eq: Net heat given by the equipment
        f_load: Fraction of load (0-1)
        """
        nom_capacity = self.parameter("nominal_heating_capacity").value
        if nom_capacity > 0:
            # variables dictonary
            var_dic = self._var_state_dic([T_wo, T_ci,T_wbci,F_water,1]) #Full load
            # Capacity
            capacity = nom_capacity * self.parameter("heating_capacity_expression").evaluate(var_dic)
            if Q_required > capacity:
                return (capacity,1)
            else:
                f_load = Q_required/capacity
                return (Q_required, f_load)           
        else:
            return (0, 0)
    
    def get_heating_power(self,T_wo, T_ci,T_wbci,F_water,Q_required):
        """
        Returns (tot_power,COP).
        """
        nom_capacity= self.parameter("nominal_heating_capacity").value
        if nom_capacity > 0:
            Q, F_load = self.get_heating_load(T_wo, T_ci,T_wbci,F_water,Q_required)
            # variables dictonary
            var_dic = self._var_state_dic([T_wo, T_ci,T_wbci,F_water,F_load])
            # Total power
            nom_power = self.parameter("nominal_heating_power").value
            if (self.parameter("heating_power_expression").value ==  "1"): ## Use COP expression
                power = nom_power * self.parameter("heating_power_expression").evaluate(var_dic)
            else: ## Use  heating power expressions
                nom_COP = nom_capacity/nom_power
                power = Q/ (nom_COP * self.parameter("COP_expression").evaluate(var_dic))
            COP = Q/power
            return (power, COP)
        else:
            return (0,0)

#### ------ Por aquí
    
    def get_cooling_load(self,T_idb,T_iwb,T_odb,T_owb,F_air,Q_required):
        """
        Q_required: Required cooling load (negative for cooling)
        Returns (Q_eq,Q_coil,Q_lat ,f_load).
        Q_eq: Sensible net heat given by the equipment
        Q_coil: Sensible gross heat given by the coil
        Q_lat: Latent heat given by the coil
        f_load: Fraction of load (0-1)
        """
        nom_total_capacity = self.parameter("nominal_total_cooling_capacity").value
        if nom_total_capacity > 0:
            Q_required = -Q_required # Positive
            # variables dictonary
            var_dic = self._var_state_dic([T_idb, T_iwb,T_odb,T_owb,F_air,1]) #Full load
            # Total
            f = self.parameter("total_cooling_capacity_expression").evaluate(var_dic)
            total_capacity = nom_total_capacity * f
            # Sensible
            sensible_capacity = self.parameter("nominal_sensible_cooling_capacity").value
            f = self.parameter("sensible_cooling_capacity_expression").evaluate(var_dic)
            sensible_capacity = sensible_capacity * f
            if (sensible_capacity > total_capacity):
                if self.parameter("dry_coil_model").value == "SENSIBLE":
                    total_capacity = sensible_capacity
                elif self.parameter("dry_coil_model").value == "TOTAL":
                    sensible_capacity = total_capacity
            cap_eq = sensible_capacity - self.get_fan_heat(1)
            if self.get_fan_heat(0) == 0: # Q_required is equipment load
                if Q_required > cap_eq:
                    return (cap_eq,sensible_capacity,total_capacity-sensible_capacity,1)
                else:
                    F_load = Q_required/cap_eq
                    return (Q_required, Q_required+self.get_fan_heat(F_load),(total_capacity-sensible_capacity)*F_load , F_load)
            else:  # Q_requiered is coil load
                if Q_required > sensible_capacity:
                    return (cap_eq,sensible_capacity,total_capacity-sensible_capacity,1)
                else:
                    F_load = Q_required/sensible_capacity
                    return (Q_required-self.get_fan_heat(F_load), Q_required,(total_capacity-sensible_capacity)*F_load , F_load)
        else:
            return (-self.get_fan_heat(0), 0, 0, 0)

    def get_cooling_power(self,T_idb,T_iwb,T_odb,T_owb,F_air,Q_required):
        """
        Returns (power,indoor_fan_power,F_EER).
        """
        Q_eq, Q_sen, Q_lat, F_load = self.get_cooling_load(T_idb,T_iwb,T_odb,T_owb,F_air,Q_required)
        if Q_sen > 0:
            # variables dictonary
            var_dic = self._var_state_dic([T_idb, T_iwb,T_odb,T_owb,F_air,F_load])
            capacity_tot = (Q_sen+Q_lat)/F_load 
            capacity_sen = Q_sen/F_load 
            power_full = self._get_correct_cooling_power(capacity_tot,capacity_sen,var_dic)
            EER_full = capacity_tot/power_full
            F_EER = self.parameter("EER_expression").evaluate(var_dic) 
            EER = EER_full * F_EER 
            if self.parameter("indoor_fan_operation").value == "CONTINUOUS":
                fan_power = self.parameter("indoor_fan_power").value
            elif self.parameter("indoor_fan_operation").value == "CYCLING":
                fan_power = self.parameter("indoor_fan_power").value*F_load/F_EER
            return (capacity_tot*F_load/EER + fan_power, fan_power, F_EER)
        else:
            fan_power = self.get_fan_power(0)
            return (fan_power,fan_power,0)
        
    def _get_correct_cooling_power(self,total_capacity, sensible_capacity, var_dic):
        power = self.parameter("nominal_cooling_power").value
        if (sensible_capacity == total_capacity and self.parameter("power_dry_coil_correction").value):
            T_iwb_min = self._get_min_T_iwb(var_dic)
            var_dic["T_iwb"] = T_iwb_min
        f = self.parameter("cooling_power_expression").evaluate(var_dic)
        return (power * f)
                  
    def _get_min_T_iwb(self,var_dic):
        total_capacity = self.parameter("nominal_total_cooling_capacity").value
        sensible_capacity = self.parameter("nominal_sensible_cooling_capacity").value
        def func(T_iwb):
            var_dic["T_iwb"] = T_iwb
            return (sensible_capacity*self.parameter("sensible_cooling_capacity_expression").evaluate(var_dic)-
                    total_capacity*self.parameter("total_cooling_capacity_expression").evaluate(var_dic))
        root = fsolve(func, var_dic["T_iwb"],xtol=1e-3)
        return root[0]
    
    def get_fan_power(self, f_load):
        if self.parameter("indoor_fan_operation").value == "CONTINUOUS":
            return self.parameter("indoor_fan_power").value
        elif self.parameter("indoor_fan_operation").value == "CYCLING":
            return self.parameter("indoor_fan_power").value * f_load

    def get_fan_heat(self, f_load):
        return self.get_fan_power(f_load)

    def _var_state_dic(self, values):
        max = self.parameter("expression_max_values").value
        min = self.parameter("expression_min_values").value
        for i in range(len(values)):
            if (values[i] > max[i]):
                values[i] = max[i]
            elif (values[i] < min[i]):
                values[i] = min[i]
        return {"T_wo":values[0],
                "T_ci":values[1],
                "T_wbci":values[2],
                "F_water":values[3],
                "F_load":values[4]}




        