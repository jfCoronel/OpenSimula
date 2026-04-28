from opensimula.Message import Message
from opensimula.Parameters import Parameter_float, Parameter_float_list, Parameter_math_exp, Parameter_options
from opensimula.Component import Component

class Chiller_heat_pump(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Chiller"
        self.parameter("description").value = "Chiller equipment manufacturer information"
        self.add_parameter(Parameter_options("chiller_type", "CHILLER", ["CHILLER", "HEAT_PUMP", "CHILLER_HEAT_PUMP"]))
        self.add_parameter(Parameter_options("condensation_type", "AIR_CONDENSED", ["AIR_CONDENSED", "WATER_CONDENSED"]))
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
        if self.parameter("chiller_type").value == "CHILLER":
             return (0, 0)
        else:
            # variables dictonary
            var_dic = self._var_state_dic([T_wo, T_ci,T_wbci,F_water,1]) #Full load
            # Capacity
            nom_capacity = self.parameter("nominal_heating_capacity").value
            capacity = nom_capacity * self.parameter("heating_capacity_expression").evaluate(var_dic)
            if Q_required > capacity:
                return (capacity,1)
            else:
                f_load = Q_required/capacity
                return (Q_required, f_load)           
           
    def get_heating_power(self,T_wo, T_ci,T_wbci,F_water,Q_required):
        """
        Returns (tot_power,COP).
        """        
        if self.parameter("chiller_type").value == "CHILLER":
            return (0,0)
        else:
            Q, F_load = self.get_heating_load(T_wo, T_ci,T_wbci,F_water,Q_required)
            # variables dictonary
            var_dic = self._var_state_dic([T_wo, T_ci,T_wbci,F_water,F_load])
            # Total power
            nom_power = self.parameter("nominal_heating_power").value
            if (self.parameter("heating_power_expression").value ==  "1"): ## Use COP expression
                nom_capacity= self.parameter("nominal_heating_capacity").value
                nom_COP = nom_capacity/nom_power
                power = Q/ (nom_COP * self.parameter("COP_expression").evaluate(var_dic))
            else: ## Use  heating power expressions
                power = nom_power * self.parameter("heating_power_expression").evaluate(var_dic)
            COP = Q/power
            return (power, COP)
            
    def get_cooling_load(self,T_wo,T_ci,T_wbci,F_water,Q_required):
        """
        Q_required: Required cooling load
        Returns (Q_eq,f_load).
        Q_eq: Total cool given by the equipment
        f_load: Fraction of load (0-1)
        """
        if self.parameter("chiller_type").value == "HEAT_PUMP":
            return (0,0)
        else:
            nom_capacity = self.parameter("nominal_cooling_capacity").value
            # variables dictonary
            var_dic = self._var_state_dic([T_wo,T_ci,T_wbci,F_water,1]) #Full load
            capacity = nom_capacity * self.parameter("cooling_capacity_expression").evaluate(var_dic)
            if Q_required > capacity:
                return (capacity,1)
            else:
                f_load = Q_required/capacity
                return (Q_required, f_load)   

    def get_cooling_power(self,T_wo, T_ci,T_wbci,F_water,Q_required):
        """
        Returns (tot_power,EER).
        """        
        if self.parameter("chiller_type").value == "HEAT_PUMP":
            return (0,0)
        else:
            Q, F_load = self.get_cooling_load(T_wo, T_ci,T_wbci,F_water,Q_required)
            # variables dictonary
            var_dic = self._var_state_dic([T_wo, T_ci,T_wbci,F_water,F_load])
            # Power
            nom_power = self.parameter("nominal_cooling_power").value
            if (self.parameter("cooling_power_expression").value ==  "1"): ## Use EER expression
                nom_capacity= self.parameter("nominal_cooling_capacity").value
                nom_EER = nom_capacity/nom_power
                power = Q/ (nom_EER * self.parameter("EER_expression").evaluate(var_dic))
            else: ## Use cooling power expressions
                power = nom_power * self.parameter("cooling_power_expression").evaluate(var_dic)
            COP = Q/power
            return (power, COP)

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




        