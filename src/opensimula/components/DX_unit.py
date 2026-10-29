from opensimula.Message import Message
from opensimula.Parameters import Parameter_float, Parameter_float_list, Parameter_math_exp, Parameter_options, Parameter_boolean
from opensimula.Component import Component
from scipy.optimize import fsolve, brentq
import math
import psychrolib as sicro

class DX_unit(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "DX_unit"
        self.parameter("description").value = "Direct Expansion unit manufacturer information"
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
        self.add_parameter(Parameter_options("dry_coil_model", "SENSIBLE", ["TOTAL", "SENSIBLE", "ADP"]))
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
        
    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._A_0 = None  # Bypass factor constant, calculated at the first cooling call
        self._T_iwb_dry = None

    def get_heating_load(self,T_idb,T_iwb,T_odb,T_owb,F_air,Q_required):
        """
        Q_required: Required heating load
        Returns (Q_eq,Q_coil,f_load).
        Q_eq: Net heat given by the equipment
        Q_coil: Gross heat given by the coil
        f_load: Fraction of load (0-1)
        """
        capacity = self.parameter("nominal_heating_capacity").value
        if capacity > 0:
            # variables dictonary
            var_dic = self._var_state_dic([T_idb, T_iwb,T_odb,T_owb,F_air,1]) #Full load
            # Capacity
            cap_coil = capacity * self.parameter("heating_capacity_expression").evaluate(var_dic)
            cap_eq = cap_coil + self.get_fan_heat(1)
            if self.get_fan_heat(0) == 0: # Q_required is equipment load
                if Q_required > cap_eq:
                    return (cap_eq,cap_coil,1)
                else:
                    f_load = Q_required/cap_eq
                    return (Q_required, Q_required-self.get_fan_heat(f_load), f_load)
            else: # Q_required is coil load
                if Q_required > cap_coil:
                    return (cap_eq,cap_coil,1)
                else:
                    f_load = Q_required/cap_coil
                    return (Q_required+self.get_fan_heat(f_load), Q_required, f_load)           
        else:
            return (self.get_fan_heat(0),0, 0)
    
    def get_heating_power(self,T_idb, T_iwb,T_odb,T_owb,F_air,Q_required):
        """
        Returns (power,indoor_fan_power,F_COP).
        """
        cap_nom = self.parameter("nominal_heating_capacity").value
        if cap_nom > 0:
            Q_eq, Q_coil, F_load = self.get_heating_load(T_idb, T_iwb,T_odb,T_owb,F_air,Q_required)
            # variables dictonary
            var_dic = self._var_state_dic([T_idb, T_iwb,T_odb,T_owb,F_air,F_load])
            # Compressor
            power_full = self.parameter("nominal_heating_power").value
            power_full = power_full * self.parameter("heating_power_expression").evaluate(var_dic)
            capacity = Q_coil/F_load 
            COP_full = capacity/power_full
            F_COP = self.parameter("COP_expression").evaluate(var_dic) 
            COP = COP_full * F_COP
            if self.parameter("indoor_fan_operation").value == "CONTINUOUS":
                fan_power = self.parameter("indoor_fan_power").value
            elif self.parameter("indoor_fan_operation").value == "CYCLING":
                fan_power = self.parameter("indoor_fan_power").value*F_load/F_COP
            return (capacity*F_load/COP + fan_power, fan_power, F_COP)
        else:
            fan_power = self.get_fan_power(0)
            return (fan_power,fan_power,0)

    
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
            self._T_iwb_dry = None
            if self.parameter("dry_coil_model").value == "ADP":
                total_capacity, sensible_capacity = self._adp_capacities(
                    T_idb, T_iwb, T_odb, T_owb, F_air, total_capacity, sensible_capacity)
            elif (sensible_capacity > total_capacity):
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
        if self.parameter("dry_coil_model").value == "ADP":
            if self._T_iwb_dry is not None and self.parameter("power_dry_coil_correction").value:
                var_dic["T_iwb"] = self._T_iwb_dry
        elif (sensible_capacity == total_capacity and self.parameter("power_dry_coil_correction").value):
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
    
    # Apparatus dew point (ADP) / bypass factor (BF) dry coil model:
    # BF = exp(-A_0/m), A_0 from the nominal capacities; the coil is dry when the humidity
    # ratio of the ADP is not below the inlet one.
    def _adp_capacities(self, T_idb, T_iwb, T_odb, T_owb, F_air, total_capacity, sensible_capacity):
        p = self._sim_.props["ATM_PRESSURE"]
        if getattr(self, "_A_0", None) is None:  # also used outside a simulation
            self._A_0 = self._get_A_0(p)
        w_in = sicro.GetHumRatioFromTWetBulb(T_idb, min(T_iwb, T_idb), p)
        m_air = self._air_mass_flow(T_idb, w_in, F_air, p)
        w_adp, SHR = self._adp_state(T_idb, w_in, m_air, total_capacity, p)
        if w_adp >= w_in:  # Dry coil: capacity at the wet bulb of the dry/wet boundary
            T_iwb_dry = self._get_dry_T_iwb(T_idb, T_iwb, T_odb, T_owb, F_air, m_air, p)
            var_dic = self._var_state_dic([T_idb, T_iwb_dry, T_odb, T_owb, F_air, 1])
            total_capacity = (self.parameter("nominal_total_cooling_capacity").value
                              * self.parameter("total_cooling_capacity_expression").evaluate(var_dic))
            self._T_iwb_dry = T_iwb_dry
            return (total_capacity, total_capacity)
        # Wet coil: the latent capacity cannot exceed that of the ADP model
        sensible_capacity = max(sensible_capacity, total_capacity * SHR)
        if sensible_capacity > total_capacity:
            total_capacity = sensible_capacity
        return (total_capacity, sensible_capacity)

    def _get_A_0(self, p):
        T_idb, T_iwb, _ = self.parameter("nominal_cooling_conditions").value
        Q_tot = self.parameter("nominal_total_cooling_capacity").value
        Q_sen = self.parameter("nominal_sensible_cooling_capacity").value
        w_in = sicro.GetHumRatioFromTWetBulb(T_idb, T_iwb, p)
        m_air = self._air_mass_flow(T_idb, w_in, 1, p)
        h_in = sicro.GetMoistAirEnthalpy(T_idb, w_in)
        h_out = h_in - Q_tot / m_air
        c_p = sicro.GetMoistAirEnthalpy(1, w_in) - sicro.GetMoistAirEnthalpy(0, w_in)
        T_out = T_idb - Q_sen / (m_air * c_p)
        w_out = sicro.GetHumRatioFromEnthalpyAndTDryBulb(h_out, T_out)
        # ADP: the line through inlet and outlet states meets the saturation curve
        def func(T):
            return sicro.GetSatHumRatio(T, p) - (w_in + (w_out - w_in) * (T - T_idb) / (T_out - T_idb))
        T_adp = brentq(func, -40, T_out)
        BF = (T_out - T_adp) / (T_idb - T_adp)
        return -math.log(BF) * m_air

    def _air_mass_flow(self, T_idb, w_in, F_air, p):
        return self.parameter("nominal_air_flow").value * F_air / sicro.GetMoistAirVolume(T_idb, w_in, p)

    def _adp_state(self, T_idb, w_in, m_air, total_capacity, p):
        """Humidity ratio of the ADP and sensible heat ratio for the given total capacity"""
        BF = math.exp(-self._A_0 / m_air)
        h_in = sicro.GetMoistAirEnthalpy(T_idb, w_in)
        h_adp = h_in - total_capacity / m_air / (1 - BF)
        if h_adp >= sicro.GetSatAirEnthalpy(T_idb, p):  # No capacity: dry
            return (sicro.GetSatHumRatio(T_idb, p), 1)
        if h_adp <= sicro.GetSatAirEnthalpy(-60, p):
            return (0, 0)
        T_adp = brentq(lambda T: sicro.GetSatAirEnthalpy(T, p) - h_adp, -60, T_idb)
        w_adp = sicro.GetSatHumRatio(T_adp, p)
        h_tin_wadp = sicro.GetMoistAirEnthalpy(T_idb, w_adp)
        SHR = min((h_tin_wadp - h_adp) / (h_in - h_adp), 1)
        return (w_adp, SHR)

    def _get_dry_T_iwb(self, T_idb, T_iwb, T_odb, T_owb, F_air, m_air, p):
        """Inlet wet bulb temperature at which the coil starts to be wet"""
        def func(T_wb):
            var_dic = self._var_state_dic([T_idb, T_wb, T_odb, T_owb, F_air, 1])
            total = (self.parameter("nominal_total_cooling_capacity").value
                     * self.parameter("total_cooling_capacity_expression").evaluate(var_dic))
            w = sicro.GetHumRatioFromTWetBulb(T_idb, T_wb, p)
            return self._adp_state(T_idb, w, m_air, total, p)[0] - w
        T_wb_min = min(T_iwb, T_idb)
        if func(T_idb) >= 0:  # Dry even at saturation
            return T_idb
        return brentq(func, T_wb_min, T_idb, xtol=1e-3)

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




        