from OpenSimula.Message import Message
from OpenSimula.Parameters import Parameter_float, Parameter_float_list, Parameter_math_exp, Parameter_options, Parameter_boolean
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
        self.add_parameter(Parameter_float("nominal_cooling_power", 0, "W", min=0))
        self.add_parameter(Parameter_float("indoor_fan_power", 0, "W", min=0))
        self.add_parameter(Parameter_float_list("nominal_cooling_conditions", [27, 19, 35], "ºC"))
        self.add_parameter(Parameter_math_exp("total_cooling_capacity_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("sensible_cooling_capacity_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("cooling_power_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("EER_expression", "1", "frac"))
        self.add_parameter(Parameter_float("nominal_heating_capacity", 0, "W", min=0))
        self.add_parameter(Parameter_float("nominal_heating_power", 0, "W", min=0))
        self.add_parameter(Parameter_float_list("nominal_heating_conditions", [20, 7, 6], "ºC"))
        self.add_parameter(Parameter_math_exp("heating_capacity_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("heating_power_expression", "1", "frac"))
        self.add_parameter(Parameter_math_exp("COP_expression", "1", "frac"))
        self.add_parameter(Parameter_options("dry_coil_model", "SENSIBLE", ["TOTAL", "SENSIBLE"]))
        self.add_parameter(Parameter_options("indoor_fan_operation", "CONTINUOUS", ["CONTINUOUS", "CYCLING"]))
        self.add_parameter(Parameter_boolean("power_dry_coil_correction", True))
        self.add_parameter(Parameter_float_list("expression_max_values", [60,30,60,30,1.5,1], "-"))
        self.add_parameter(Parameter_float_list("expression_min_values", [0,0,-30,-30,0,0], "-"))

    def check(self):
        errors = super().check()
        # Test Cooling and Heating conditions 3 values
        if len(self.parameter("nominal_cooling_conditions").value)!= 3:
            msg = f"Error: {self.parameter('name').value}, nominal_cooling_conditions size must be 3"
            errors.append(Message(msg, "ERROR"))
        if len(self.parameter("nominal_heating_conditions").value)!= 3:
            msg = f"Error: {self.parameter('name').value}, nominal_heating_conditions size must be 3"
            errors.append(Message(msg, "ERROR"))
        return errors
    
    def get_cooling_capacity(self,T_idb,T_iwb,T_odb,T_owb,F_air):
        """
        Returns (Q_tot,Q_sen) capacities. 
        If indoor_fan_operation is CONTINUOUS: It returns the values from the expressions (Gross capacity = Coil capacity)
        If indoor_fan_operation is CYCLING: It returns the expressions minus the indoor fan power (Net capacity = Gross capacity - indoor fan)  
        """
        total_capacity = self.parameter("nominal_total_cooling_capacity").value
        if total_capacity > 0:
            # variables dictonary
            var_dic = self._var_state_dic([T_idb, T_iwb,T_odb,T_owb,F_air,0])
            # Total
            f = self.parameter("total_cooling_capacity_expression").evaluate(var_dic)
            total_capacity = total_capacity * f
            # Sensible
            sensible_capacity = self.parameter("nominal_sensible_cooling_capacity").value
            f = self.parameter("sensible_cooling_capacity_expression").evaluate(var_dic)
            sensible_capacity = sensible_capacity * f
            if (sensible_capacity > total_capacity):
                if self.parameter("dry_coil_model").value == "SENSIBLE":
                    total_capacity = sensible_capacity
                elif self.parameter("dry_coil_model").value == "TOTAL":
                    sensible_capacity = total_capacity
            if self.parameter("indoor_fan_operation").value == "CYCLING":
                sensible_capacity = sensible_capacity - self.get_fan_heat(1)
                total_capacity = total_capacity - self.get_fan_heat(1)
            return (total_capacity, sensible_capacity)
        else:
            return (0,0)
    
    def get_heating_capacity(self,T_idb,T_iwb,T_odb,T_owb,F_air):
        """
        Returns heat sensible capacity. 
        If indoor_fan_operation is CONTINUOUS: It returns the values from the expressions (Gross capacity = Coil capacity)
        If indoor_fan_operation is CYCLING: It returns the expressions plus the indoor fan power (Net capacity = Gross capacity + indoor fan)  """
        capacity = self.parameter("nominal_heating_capacity").value
        if capacity > 0:
            # variables dictonary
            var_dic = self._var_state_dic([T_idb, T_iwb,T_odb,T_owb,F_air,0])
            # Capacity
            capacity = capacity * self.parameter("heating_capacity_expression").evaluate(var_dic)
            if self.parameter("indoor_fan_operation").value == "CYCLING":
                capacity = capacity + self.get_fan_heat(1)
            return capacity
        else:
            return 0
    
    def get_cooling_state(self,T_idb,T_iwb,T_odb,T_owb,F_air,F_load):
        """
        Returns (Q_tot,Q_sen,power,indoor_fan_power,F_EER).
        """
        total_capacity, sensible_capacity = self.get_cooling_capacity(T_idb,T_iwb,T_odb,T_owb,F_air)
        if total_capacity > 0:
            if self.parameter("indoor_fan_operation").value == "CYCLING": # Get gross capacities
                total_capacity= total_capacity + self.get_fan_heat(1)
                sensible_capacity= sensible_capacity + self.get_fan_heat(1)
            if (F_load > 0):
                # variables dictonary
                var_dic = self._var_state_dic([T_idb, T_iwb,T_odb,T_owb,F_air,F_load])
                # con
                power_full = self._get_correct_cooling_power(total_capacity,sensible_capacity,var_dic)

                EER_full = total_capacity/power_full
                F_EER = self.parameter("EER_expression").evaluate(var_dic) 
                EER = EER_full * F_EER 
                if self.parameter("indoor_fan_operation").value == "CONTINUOUS":
                    fan_power = self.parameter("indoor_fan_power").value
                    power = total_capacity*F_load/EER + fan_power
                elif self.parameter("indoor_fan_operation").value == "CYCLING":
                    fan_power = self.parameter("indoor_fan_power").value*F_load/F_EER
                    power = total_capacity*F_load/EER + fan_power 
                return (total_capacity*F_load, sensible_capacity*F_load, power, fan_power, F_EER)
            else:
                fan_power = self.get_fan_power(0)
                return (0,fan_power,fan_power,0)
        else:
            return (0,0,0,0,0)
        
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
    
    def get_heating_state(self,T_idb, T_iwb,T_odb,T_owb,F_air,F_load):
        """
        Returns (Q_sen,power,indoor_fan_power,F_COP).
        """
        capacity = self.get_heating_capacity(T_idb, T_iwb, T_odb,T_owb,F_air)
        if self.parameter("indoor_fan_operation").value == "CYCLING": # Get gross capacities
            capacity= capacity - self.get_fan_heat(1)
        if capacity > 0:
            if (F_load > 0):
                # variables dictonary
                var_dic = self._var_state_dic([T_idb, T_iwb,T_odb,T_owb,F_air,F_load])
                # Compressor
                power_full = self.parameter("nominal_heating_power").value
                power_full = power_full * self.parameter("heating_power_expression").evaluate(var_dic)
                COP_full = capacity/power_full
                F_COP = self.parameter("COP_expression").evaluate(var_dic) 
                COP = COP_full * F_COP
                if self.parameter("indoor_fan_operation").value == "CONTINUOUS":
                    fan_power = self.parameter("indoor_fan_power").value
                    power = capacity*F_load/COP + fan_power
                elif self.parameter("indoor_fan_operation").value == "CYCLING":
                    fan_power = self.parameter("indoor_fan_power").value*F_load/F_COP
                    power = capacity*F_load/COP + fan_power
                return (capacity*F_load, power, fan_power, F_COP)
            else:
                fan_power = self.get_fan_power(0)
                return (0,fan_power,fan_power,0)
        else:
            return (0,0,0,0)
        
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
        return {"T_idb":values[0],
                "T_iwb":values[1],
                "T_odb":values[2],
                "T_owb":values[3],
                "F_air":values[4],
                "F_load":values[5]}




        