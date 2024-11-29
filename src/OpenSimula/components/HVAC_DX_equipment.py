from OpenSimula.Parameters import Parameter_float, Parameter_float_list, Parameter_math_exp, Parameter_options
from OpenSimula.Component import Component
from scipy.optimize import fsolve

class HVAC_DX_equipment(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_DX_equipment"
        self.parameter("description").value = "HVAC Direct Expansion equipment manufacturer information"
        self.add_parameter(Parameter_float("nominal_air_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("nominal_total_cooling_capacity", 0, "W", min=0))
        self.add_parameter(Parameter_float("nominal_sensible_cooling_capacity", 0, "W", min=0))
        self.add_parameter(Parameter_float("nominal_compressor_cooling_power", 0, "W", min=0))
        self.add_parameter(Parameter_float("nominal_fan_cooling_power", 0, "W", min=0))
        self.add_parameter(Parameter_float("nominal_other_cooling_power", 0, "W", min=0))
        self.add_parameter(Parameter_float_list("nominal_cooling_conditions", [27, 19, 35], "ºC"))
        self.add_parameter(Parameter_math_exp("total_cooling_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("sensible_cooling_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("compressor_cooling_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("EER_expression", "1", "frac"))
        self.add_parameter(Parameter_float("nominal_heating_capacity", 0, "W", min=0))
        self.add_parameter(Parameter_float("nominal_compressor_heating_power", 0, "W", min=0))
        self.add_parameter(Parameter_float("nominal_fan_heating_power", 0, "W", min=0))
        self.add_parameter(Parameter_float("nominal_other_heating_power", 0, "W", min=0))
        self.add_parameter(Parameter_float_list("nominal_heating_conditions", [20, 7, 6], "ºC"))
        self.add_parameter(Parameter_math_exp("capacity_heating_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("compressor_heating_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("COP_expression", "1", "frac"))
        self.add_parameter(
            Parameter_options("colling_dominant_expression", "SENSIBLE", [
                              "TOTAL", "SENSIBLE"])
        )

    def check(self):
        errors = super().check()
        # Test Cooling and Heating conditions 3 values
        if len(self.parameter("nominal_cooling_conditions").value)!= 3:
            errors.append(f"Error: {self.parameter('name').value}, nominal_cooling_conditions size must be 3")
        if len(self.parameter("nominal_heating_conditions").value)!= 3:
            errors.append(f"Error: {self.parameter('name').value}, nominal_heating_conditions size must be 3")
        return errors
    
    def get_cooling_capacity(self,T_edb,T_ewb,T_odb,F_air):
        total_capacity = self.parameter("nominal_total_cooling_capacity").value
        if total_capacity > 0:
            # variables dictonary
            var_dic = {"T_edb":T_edb,"T_ewb":T_ewb,"T_odb":T_odb,"Fair":F_air}
            # Total
            total_capacity = total_capacity * self.parameter("total_cooling_expression").evaluate(var_dic)
            # Sensible
            sensible_capacity = self.parameter("nominal_sensible_cooling_capacity").value
            sensible_capacity = sensible_capacity * self.parameter("sensible_cooling_expression").evaluate(var_dic)
            if (sensible_capacity > total_capacity):
                if self.parameter("colling_dominant_expression").value == "SENSIBLE":
                    total_capacity = sensible_capacity
                elif self.parameter("colling_dominant_expression").value == "TOTAL":
                    sensible_capacity = total_capacity
            return (total_capacity, sensible_capacity)
        else:
            return (0,0)
    
    def get_heating_capacity(self,T_edb,T_odb,T_owb,F_air):
        capacity = self.parameter("nominal_heating_capacity").value
        if capacity > 0:
            # variables dictonary
            var_dic = {"T_edb":T_edb,"T_odb":T_odb,"T_owb":T_owb,"Fair":F_air}
            # Capacity
            capacity = capacity * self.parameter("capacity_heating_expression").evaluate(var_dic)
            return capacity
        else:
            return 0
    
    def get_cooling_power(self,T_edb,T_ewb,T_odb,F_air,F_load):
        total_capacity, sensible_capacity = self.get_cooling_capacity(T_edb,T_ewb,T_odb,F_air)
        if total_capacity > 0:
            # variables dictonary
            var_dic = {"T_edb":T_edb,"T_ewb":T_ewb,"T_odb":T_odb,"F_air":F_air,"F_load":F_load}
            # Compressor
            comp_power = self.get_compresor_cooling_max_power(var_dic,total_capacity, sensible_capacity)
            comp_power = self.parameter("nominal_compressor_cooling_power").value

            comp_power = comp_power * self.parameter("compressor_cooling_expression").evaluate(var_dic)
            # Fan
            fan_power = self.parameter("nominal_fan_cooling_power").value
            # Other
            other_power = self.parameter("nominal_other_cooling_power").value
            EER_full = total_capacity/(comp_power+fan_power+other_power)
            EER = EER_full * self.parameter("EER_expression").evaluate(var_dic) 
            total_con = total_capacity*F_load/EER
            comp_power = total_con - fan_power - other_power
            return (comp_power, fan_power, other_power)
        else:
            return (0,0,0)
        
    def get_compresor_cooling_max_power(self,var_dic,total_capacity, sensible_capacity):
        comp_power = self.parameter("nominal_compressor_cooling_power").value
        if (sensible_capacity == total_capacity):
            T_ewb_min = self.get_min_T_ewb(var_dic)
            var_dic["T_ewb"] = T_ewb_min
        comp_power = comp_power * self.parameter("compressor_cooling_expression").evaluate(var_dic)
        return comp_power
    
    def get_min_T_ewb(self,var_dic):
        total_capacity = self.parameter("nominal_total_cooling_capacity").value
        sensible_capacity = self.parameter("nominal_sensible_cooling_capacity").value
        def func(T_ewb):
            var_dic["T_ewb"] = T_ewb
            return (sensible_capacity*self.parameter("sensible_cooling_expression").evaluate(var_dic)-total_capacity*self.parameter("total_cooling_expression").evaluate(var_dic))
        root = fsolve(func, var_dic["T_ewb"])
        return root
    
    def get_heating_power(self,T_edb,T_odb,T_owb,F_air,F_load):
        capacity = self.get_heating_capacity(T_edb,T_odb,T_owb,F_air)
        if capacity > 0:
            # variables dictonary
            var_dic = {"T_edb":T_edb,"T_odb":T_odb,"T_owb":T_owb,"F_air":F_air,"F_load":F_load}
            # Compressor
            comp_power = self.parameter("nominal_compressor_heating_power").value
            comp_power = comp_power * self.parameter("compressor_heating_expression").evaluate(var_dic)
            # Fan
            fan_power = self.parameter("nominal_fan_heating_power").value
            # Other
            other_power = self.parameter("nominal_other_other_power").value
            COP_full = capacity/(comp_power+fan_power+other_power)
            COP = COP_full * self.parameter("COP_expression").evaluate(var_dic) 
            total_con = capacity*F_load/COP
            comp_power = total_con - fan_power - other_power
            return (comp_power, fan_power, other_power)
        else:
            return (0,0,0)



        