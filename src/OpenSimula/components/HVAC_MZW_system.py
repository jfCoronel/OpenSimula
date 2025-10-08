import numpy as np
from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_boolean,
    Parameter_component,
    Parameter_component_list,
    Parameter_float,
    Parameter_float_list,
    Parameter_variable_list,
    Parameter_math_exp,
    Parameter_math_exp_list,
    Parameter_options
)
from opensimula.Component import Component
from opensimula.Variable import Variable
import psychrolib as sicro


class HVAC_MZW_system(Component):  # HVAC Multizone Water system
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_MZW_system"
        self.parameter("description").value = "HVAC Multizone Water system"
        self.add_parameter(
            Parameter_component_list(
                "spaces", ["not_defined", "not_defined"], ["Space"]
            )
        )
        self.add_parameter(
            Parameter_float_list(
                "air_flow_fractions", [0.5, 0.5], min=0, max=1, unit="frac"
            )
        )
        self.add_parameter(
            Parameter_component("cooling_coil", "not_defined", ["HVAC_coil_equipment"])
        )
        self.add_parameter(
            Parameter_component("heating_coil", "not_defined", ["HVAC_coil_equipment"])
        )
        self.add_parameter(
            Parameter_component("supply_fan", "not_defined", ["HVAC_fan_equipment"])
        )
        self.add_parameter(
            Parameter_component("return_fan", "not_defined", ["HVAC_fan_equipment"])
        )
        self.add_parameter(Parameter_float("air_flow", 1, "m³/s", min=0))
        self.add_parameter(
            Parameter_float("return_air_flow", 1, "m³/s", min=0)
        )  # Not used when return fan is not defined
        self.add_parameter(
            Parameter_float_list(
                "return_air_flow_fractions", [0.5, 0.5], min=0, max=1, unit="frac"
            )
        )
        self.add_parameter(
            Parameter_float_list(
                "min_air_flow_fractions", [0.3333, 0.4286], min=0, max=1, unit="frac"
            )
        )
        self.add_parameter(Parameter_math_exp("outdoor_air_fraction", "0", "frac"))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("supply_heating_setpoint", "10", "°C"))
        self.add_parameter(Parameter_math_exp("supply_cooling_setpoint", "15", "°C"))
        self.add_parameter(Parameter_math_exp_list("spaces_setpoint", ["20","20"], "°C"))
        self.add_parameter(Parameter_math_exp("system_on_off", "1", "on/off"))
        self.add_parameter(
            Parameter_options("fan_operation", "CONTINUOUS", ["CONTINUOUS", "CYCLING"])
        )
        self.add_parameter(
            Parameter_options("water_source", "UNKNOWN", ["UNKNOWN", "WATER_LOOP"])
        )
        self.add_parameter(Parameter_float("cooling_water_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("heating_water_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("inlet_cooling_water_temp", 7, "ºC"))
        self.add_parameter(Parameter_float("inlet_heating_water_temp", 50, "ºC"))
        self.add_parameter(
            Parameter_options(
                "water_flow_control", "ON_OFF", ["ON_OFF", "PROPORTIONAL"]
            )
        )
        self.add_parameter(
            Parameter_options(
                "economizer",
                "NO",
                [
                    "NO",
                    "TEMPERATURE",
                    "TEMPERATURE_NOT_INTEGRATED",
                    "ENTHALPY",
                    "ENTHALPY_LIMITED",
                ],
            )
        )
        self.add_parameter(Parameter_float("economizer_DT", 0, "ºC", min=0))
        self.add_parameter(
            Parameter_float("economizer_enthalpy_limit", 0, "kJ/kg", min=0)
        )
        self.add_parameter(Parameter_boolean("reheat", False))
        self.add_parameter(Parameter_boolean("vav", False))
        self.add_parameter(     
            Parameter_component_list(
                "reheat_coils", ["not_defined", "not_defined"], ["HVAC_coil_equipment"]
            )
        )

        # Variables
        self.add_variable(
            Variable("state", unit="flag")
        )  # 0: 0ff, 1: Heating, 2: Heating max cap, -1:Cooling, -2:Cooling max cap, 3: Venting
        self.add_variable(Variable("T_OA", unit="°C"))
        self.add_variable(Variable("T_OAwb", unit="°C"))
        self.add_variable(Variable("T_MA", unit="°C"))
        self.add_variable(Variable("T_MAwb", unit="°C"))
        self.add_variable(Variable("F_load", unit="frac"))
        self.add_variable(Variable("outdoor_air_fraction", unit="frac"))
        self.add_variable(Variable("m_air_flow", unit="kg/s"))
        self.add_variable(Variable("T_SA", unit="°C"))
        self.add_variable(Variable("w_SA", unit="g/kg"))
        self.add_variable(Variable("T_CA", unit="°C"))
        self.add_variable(Variable("w_CA", unit="g/kg"))
        self.add_variable(Variable("Q_sensible", unit="W"))
        self.add_variable(Variable("Q_latent", unit="W"))
        self.add_variable(Variable("Q_total", unit="W"))
        self.add_variable(Variable("supply_fan_power", unit="W"))
        self.add_variable(Variable("return_fan_power", unit="W"))
        self.add_variable(Variable("supply_heating_setpoint", unit="°C"))
        self.add_variable(Variable("supply_cooling_setpoint", unit="°C"))
        self.add_variable(Variable("epsilon", unit="frac"))
        self.add_variable(Variable("epsilon_adp", unit="frac"))
        self.add_variable(Variable("T_iw", unit="°C"))
        self.add_variable(Variable("T_ow", unit="°C"))
        self.add_variable(Variable("T_ADP", unit="°C"))
        self.add_variable(Variable("T_ZA", unit="°C"))  # Return air temperature, zone mixture
        self.add_variable(Variable("T_RA", unit="°C"))  # Return air temperature, after fan
        self.add_variable(Variable("w_RA", unit="g/kg"))

    def check(self):
        errors = super().check()
        # Test spaces
        if len(self.parameter("spaces").value) == 0 or any(
            x == "not_defined" for x in self.parameter("spaces").value
        ):
            msg = "spaces have not been correctly defined"
            errors.append(Message(msg, "ERROR"))
        # Test air fractions
        if len(self.parameter("air_flow_fractions").value) != len(
            self.parameter("spaces").value
        ):
            msg = "air_flow_fractions must have the same number of elements as spaces"
            errors.append(Message(msg, "ERROR"))
        # Test air fractions sum equal to 1
        if abs(sum(self.parameter("air_flow_fractions").value) - 1) > 0.0001:
            msg = "air_flow_fractions must sum equal to 1"
            errors.append(Message(msg, "ERROR"))
        # Test return air fractions
        if len(self.parameter("return_air_flow_fractions").value) != len(
            self.parameter("spaces").value
        ):
            msg = "return_air_flow_fractions must have the same number of elements as spaces"
            errors.append(Message(msg, "ERROR"))
        # Test air fractions sum equal to 1
        if abs(sum(self.parameter("return_air_flow_fractions").value) - 1) > 0.0001:
            msg = "return_air_flow_fractions must sum equal to 1"
            errors.append(Message(msg, "ERROR"))
        # Test supply fan defined
        if self.parameter("supply_fan").value == "not_defined":
            msg = (
                f"{self.parameter('name').value}, must define its supply fan equipment."
            )
            errors.append(Message(msg, "ERROR"))
        # Test file_met defined
        if self.project().parameter("simulation_file_met").value == "not_defined":
            msg = f"{self.parameter('name').value}, file_met must be defined in the project 'simulation_file_met'."
            errors.append(Message(msg, "ERROR"))
        
        return errors
       

    def pre_simulation(self, n_time_steps, delta_t):
        # Add variables before pre_simulation of Component
        self.spaces = self.parameter("spaces").component
        for i in range(len(self.spaces)):
            self.add_variable(Variable(f"spaces_setpoint_{i}", unit="°C"))
            self.add_variable(Variable(f"Q_reheat_{i}", unit="W"))
            self.add_variable(Variable(f"T_SA_{i}", unit="°C"))
            self.add_variable(Variable(f"m_air_flow_{i}", unit="kg/s"))

        super().pre_simulation(n_time_steps, delta_t)
        # Sicro
        sicro.SetUnitSystem(sicro.SI)
        self.props = self._sim_.props
        self.file_met = self.project().parameter("simulation_file_met").component

        # Parameters
        self.air_flow_fractions = self.parameter("air_flow_fractions").value
        self.return_air_flow_fractions = self.parameter("return_air_flow_fractions").value
        self.min_air_flow_fractions = self.parameter("min_air_flow_fractions").value
        self.c_coil = self.parameter("cooling_coil").component
        self.h_coil = self.parameter("heating_coil").component
        self.supply_fan = self.parameter("supply_fan").component
        self.return_fan = self.parameter("return_fan").component
        self.air_flow = self.parameter("air_flow").value
        self.return_air_flow = self.parameter("return_air_flow").value
        self.reheat_coils = self.parameter("reheat_coils").component

        # Water flows and temperatures
        self.cooling_water_flow = self.parameter("cooling_water_flow").value
        self.heating_water_flow = self.parameter("heating_water_flow").value
        if self.c_coil:
            self._cooling_F_water = (
                self.cooling_water_flow
                / self.c_coil.parameter("nominal_cooling_water_flow").value
            )
        if self.h_coil:
            self._heating_F_water = (
                self.heating_water_flow
                / self.h_coil.parameter("nominal_heating_water_flow").value
            )
        self.cooling_water_temp = self.parameter("inlet_cooling_water_temp").value
        self.heating_water_temp = self.parameter("inlet_heating_water_temp").value
        self.rho_MA = self.props["RHO_A"]
        # Fan operation
        self.fan_operation = self.parameter("fan_operation").value
        # adp model
        self.water_flow_control = self.parameter("water_flow_control").value
        # VAV, REHEAT
        self.is_vav = self.parameter("vav").value
        self.is_reheat = self.parameter("reheat").value
        self.supply_return_flow_ratio = np.ones(len(self.spaces))
        for i in range(len(self.spaces)):
            self.supply_return_flow_ratio[i] = (self.air_flow*self.air_flow_fractions[i])/(self.return_air_flow*self.return_air_flow_fractions[i])

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        # Outdoor air
        self.T_OA = self.file_met.variable("temperature").values[time_index]
        self.T_OAwb = self.file_met.variable("wet_bulb_temp").values[time_index]
        self.w_OA = self.file_met.variable("abs_humidity").values[time_index]
        self.variable("T_OA").values[time_index] = self.T_OA
        self.variable("T_OAwb").values[time_index] = self.T_OAwb
        self.rho_OA = 1 / sicro.GetMoistAirVolume(
            self.T_OA, self.w_OA / 1000, self.props["ATM_PRESSURE"]
        )

        # variables dictonary
        var_dic = self.get_parameter_variable_dictionary(time_index)
        # outdoor air fraction
        self.F_OA_min = self.parameter("outdoor_air_fraction").evaluate(var_dic)
        self.F_OA = self.F_OA_min
        # setpoints
        self.T_heat_sp = self.parameter("supply_heating_setpoint").evaluate(var_dic)
        self.variable("supply_heating_setpoint").values[time_index] = self.T_heat_sp
        self.T_cool_sp = self.parameter("supply_cooling_setpoint").evaluate(var_dic)
        self.variable("supply_cooling_setpoint").values[time_index] = self.T_cool_sp
        if self.is_reheat or self.is_vav:
            self.T_space_sp = []
            for i in range(len(self.parameter("spaces").value)):
                val = self.parameter("spaces_setpoint").evaluate(i,var_dic)
                self.T_space_sp.append(val)
                self.variable(f"spaces_setpoint_{i}").values[time_index] = val
        # on/off
        self.on_off = self.parameter("system_on_off").evaluate(var_dic)
        if self.on_off == 0:
            self.state = 0
            self.variable("state").values[time_index] = 0
            self.on_off = False
        else:
            self.on_off = True
        # Starting with the system venting
        self.F_load = 0
        self.epsilon = 0
        self.epsilon_adp = 0
        self.total_vav_supply_fraction = 1.0
        self.vav_supply_fraction = np.ones(len(self.spaces))


    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)
        if self.on_off:
            self._calculate_return_air(time_index)
            self._calculate_mixed_air()
            self._calculate_required_Q()
            if self.parameter("economizer").value != "NO":
                self._simulate_economizer()  # Calculation of new f_oa
                self._calculate_mixed_air()
                self._calculate_required_Q()
            self._simulate_system()
            self._send_air_to_spaces(time_index)
        return True

    def _calculate_return_air(self, time_index):
        # Return fan
        if self.return_fan is None:  # No return fan
            self.m_return = self.air_flow * (1 - self.F_OA) * self.rho_MA
        else:
            if self.is_vav:
                self.m_return = 0
                for i in range(len(self.spaces)):
                    self.m_return += self.air_flow * self.air_flow_fractions[i] * self.supply_return_flow_ratio[i] * self.vav_supply_fraction[i] * self.rho_MA
            else:
                self.m_return = self.return_air_flow * self.rho_MA
            # Calculate flow fraction in return fan
            return_flow_fraction = self.m_return / (self.return_air_flow * self.rho_MA)
            Q_return_fan = self._get_fan_power("return", self.F_load, return_flow_fraction)
        self.T_RA = 0
        self.T_ZA = 0
        self.w_RA = 0
        for i in range(len(self.spaces)):
            space = self.spaces[i]
            f_return = self.return_air_flow_fractions[i]
            self.T_ZA += f_return * space.variable("temperature").values[time_index]
            self.w_RA += f_return * space.variable("abs_humidity").values[time_index]
        if Q_return_fan > 0 and self.m_return > 0:
            self.T_RA = Q_return_fan / (self.m_return * self.props["C_PA"]) + self.T_ZA
        else: 
            self.T_RA = self.T_ZA

    def _calculate_mixed_air(self):
        # Mixed air
        self.F_OA = self.F_OA_min/self.total_vav_supply_fraction
        self.T_MA, self.w_MA, self.T_MAwb = self._mix_air(
            self.F_OA, self.T_OA, self.w_OA, self.T_RA, self.w_RA
        )
        self.rho_MA = 1 / sicro.GetMoistAirVolume(
            self.T_MA, self.w_MA / 1000, self.props["ATM_PRESSURE"]
        )

    def _mix_air(self, f, T1, w1, T2, w2):
        T = f * T1 + (1 - f) * T2
        w = f * w1 + (1 - f) * w2
        if T > 100:
            T_wb = 50  # Inventado
        else:
            T_wb = sicro.GetTWetBulbFromHumRatio(
                T, w / 1000, self.props["ATM_PRESSURE"]
            )
        return (T, w, T_wb)

    def _calculate_required_Q(self):
        # Calculate the required Q to mantain the supply air temperature
        m_cp = self.air_flow * self.total_vav_supply_fraction * self.rho_MA * self.props["C_PA"]
        T_with_fan = self._get_fan_power("supply", self.F_load, self.total_vav_supply_fraction) / m_cp + self.T_MA
        if T_with_fan < self.T_heat_sp:
            self.Q_required = m_cp * (self.T_heat_sp - T_with_fan)
        elif T_with_fan > self.T_cool_sp:
            self.Q_required = m_cp * (self.T_cool_sp - T_with_fan)
        else:
            self.Q_required = 0
        if abs(self.Q_required) < 0.0001:  # Problems with convergence
            self.Q_required = 0

    def _get_fan_power(self, fan, f_load, f_flow=1):
        if self.is_vav:
            if fan == "supply":
                return self.supply_fan.get_power(self.air_flow * f_flow)
            elif fan == "return":
                if self.return_fan is None:  # No return fan
                    return 0
                else:
                    return self.return_fan.get_power(self.return_air_flow * f_flow)
        else:
            if fan == "supply":
                if self.fan_operation == "CONTINUOUS":
                    return self.supply_fan.get_power(self.air_flow)
                elif self.fan_operation == "CYCLING":
                    return self.supply_fan.get_power(self.air_flow) * f_load
            elif fan == "return":
                if self.return_fan is None:  # No return fan
                    return 0
                else:
                    if self.fan_operation == "CONTINUOUS":
                        return self.return_fan.get_power(self.return_air_flow)
                    elif self.fan_operation == "CYCLING":
                        return self.return_fan.get_power(self.return_air_flow) * f_load

    def _simulate_economizer(self):
        if (
            self.parameter("economizer").value == "TEMPERATURE"
            or self.parameter("economizer").value == "TEMPERATURE_NOT_INTEGRATED"
        ):
            on_economizer = (
                self.T_OA < self.T_RA - self.parameter("economizer_DT").value
            )
        elif self.parameter("economizer").value == "ENTHALPY":
            h_OA = sicro.GetMoistAirEnthalpy(self.T_OA, self.w_OA / 1000)
            h_RA = sicro.GetMoistAirEnthalpy(self.T_RA, self.w_RA / 1000)
            on_economizer = h_OA < h_RA
        elif self.parameter("economizer").value == "ENTHALPY_LIMITED":
            h_OA = sicro.GetMoistAirEnthalpy(self.T_OA, self.w_OA / 1000)
            on_economizer = (
                h_OA < self.parameter("economizer_enthalpy_limit").value * 1000
            )

        if on_economizer:
            if self.Q_required < 0:
                mrhocp = self.air_flow * self.props["C_PA"] * self.rho_OA
                Q_rest_oa = mrhocp * (1 - self.F_OA) * (self.T_OA - self.T_cool_sp)
                if Q_rest_oa < self.Q_required:
                    self.F_OA += self.Q_required / (
                        mrhocp * (self.T_OA - self.T_cool_sp)
                    )
                    self._Q_required = 0
                else:
                    if (
                        self.parameter("economizer").value
                        == "TEMPERATURE_NOT_INTEGRATED"
                    ):
                        self.F_OA = self.F_OA_min
                    else:
                        self.F_OA = 1
            elif self.Q_required > 0:  # Heating
                self.F_OA = self.F_OA_min
        else:
            self.F_OA = self.F_OA_min

    def _simulate_system(self):
        if self.h_coil is not None and self.Q_required > 0:  # Heating
            self._simulate_heating()
        elif self.c_coil is not None and self.Q_required < 0:  # Cooling
            self._simulate_cooling()
        else:  # Venting
            self.state = 3
            self.F_load = 0
            self.Q_coil = 0
            self.T_CA = self.T_MA
            self.w_CA = self.w_MA
        # Calculate supply air temperature with fan power
        m_supply = self.air_flow * self.rho_MA * self.total_vav_supply_fraction
        if m_supply > 0:
            self.T_SA = self.T_CA + self._get_fan_power("supply", self.F_load, self.total_vav_supply_fraction) / (
                m_supply * self.props["C_PA"]
            )
        else:
            self.T_SA = self.T_CA
        self.w_SA = self.w_CA
        self.T_SAwb = sicro.GetTWetBulbFromHumRatio(self.T_SA,self.w_SA/1000, self.props["ATM_PRESSURE"])

    def _simulate_heating(self):
        capacity, self.epsilon = self.h_coil.get_heating_capacity(
            self.T_MA,
            self.T_MAwb,
            self.heating_water_temp,
            self.air_flow*self.total_vav_supply_fraction,
            self.heating_water_flow,
        )
        self.M_w = 0  # No latent load in heating
        # Q_required is only the coil capacity
        if capacity < self.Q_required:  # Coil capacity is not enough
            self.F_load = 1
            self.Q_coil = capacity
            self.state = 2
        else:
            self.Q_coil = self.Q_required
            self.F_load = self.Q_coil / capacity
            self.state = 1
        self.T_CA = self.T_MA + self.Q_coil / (
            self.air_flow * self.total_vav_supply_fraction* self.rho_MA * self.props["C_PA"]
        )
        self.w_CA = self.w_MA
        

    def _simulate_cooling(self):
        capacity_sen, capacity_lat, self.T_ADP, self.epsilon, self.epsilon_adp = (
            self.c_coil.get_cooling_capacity(
                self.T_MA,
                self.T_MAwb,
                self.cooling_water_temp,
                self.air_flow*self.total_vav_supply_fraction,
                self.cooling_water_flow,
            )
        )
        Q_required = -self.Q_required
        # Q_required is only the coil capacity
        if capacity_sen < Q_required:  # Coil capacity is not enough
            self.state = -2
            self.F_load = 1
            self.Q_coil = -capacity_sen
            self.M_w = -(capacity_lat) / self.props["LAMBDA"]
        else:
            self.state = -1
            self.Q_coil = -Q_required
            self.F_load = Q_required / capacity_sen
            if self.water_flow_control == "ON_OFF":
                self.M_w = -(capacity_lat * self.F_load) / self.props["LAMBDA"]
            elif self.water_flow_control == "PROPORTIONAL":
                mrhocp = self.air_flow * self.total_vav_supply_fraction * self.rho_MA * self.props["C_PA"]
                T_CA = self.T_MA - (Q_required) / mrhocp
                Q_lat, self.T_ADP, self.epsilon_adp = (
                    self.c_coil.get_latent_cooling_load(
                        self.T_MA,
                        self.T_MAwb,
                        self.cooling_water_temp,
                        self.air_flow*self.total_vav_supply_fraction,
                        self.cooling_water_flow,
                        T_CA,
                    )
                )
                self.M_w = -Q_lat / self.props["LAMBDA"]
        self.T_CA = self.T_MA + self.Q_coil / (
            self.air_flow * self.total_vav_supply_fraction * self.rho_MA * self.props["C_PA"]
        )
        self.w_CA = self.w_MA + self.M_w / (self.air_flow * self.total_vav_supply_fraction * self.rho_MA)

    def _send_air_to_spaces(self, time_index): 
        self.Q_reheat = np.zeros(len(self.spaces))
        self.total_vav_supply_fraction = 0
        for i in range(len(self.spaces)):
            space = self.spaces[i]
            reheat_needed = True
            f_air_flow = 1.0
            air_flow = {
                "name": self.parameter("name").value,
                "M_a": 0,
                "T_a": self.T_SA,
                "w_a": self.w_SA,
                "Q_s": 0,
                "M_w": 0,
            }
            # Remove flow
            space.add_uncontrol_system(air_flow)
            if self.is_vav:
                f_air_flow = self._get_vav_supply_fraction_required(i, space)
                reheat_needed = False
                if f_air_flow > 1.0:
                    f_air_flow = 1.0
                elif f_air_flow < self.min_air_flow_fractions[i]:
                    f_air_flow = self.min_air_flow_fractions[i]
                    reheat_needed = True
            
            self.vav_supply_fraction[i] = f_air_flow
            self.total_vav_supply_fraction += self.air_flow_fractions[i] * f_air_flow
            air_flow["M_a"] = self.air_flow * self.rho_MA * self.air_flow_fractions[i] * f_air_flow
            # Always added as uncontrolled system, reheat is added as controlled if needed
            space.add_uncontrol_system(air_flow)
           

            if self.is_reheat:
                reheat_coil = self.reheat_coils[i]
                if reheat_coil is not None and reheat_needed:
                    # Reheat coil
                    water_flow = reheat_coil.parameter("nominal_heating_water_flow").value
                    capacity, epsilon = reheat_coil.get_heating_capacity(
                            self.T_SA,
                            self.T_SAwb,
                            self.heating_water_temp,
                            self.air_flow * f_air_flow,
                            water_flow,
                    )
                    Q_reheat_required = self._get_Q_reheat_required(i, space)
                    if capacity > Q_reheat_required:
                        self.Q_reheat[i]= Q_reheat_required
                    else:
                        self.Q_reheat[i]= capacity
                    space.set_control_system({"M_a": 0,"T_a": 0,"w_a": 0,"Q_s": self.Q_reheat[i],"M_w": 0})

    def _get_vav_supply_fraction_required(self, i, space):
        K_t,F_t = space.get_thermal_equation(False)
        T_flo = F_t/K_t
        if T_flo < self.T_space_sp[i]:
            Q_sens_required =  K_t * self.T_space_sp[i] - F_t
            Q_system_max = self.air_flow * self.rho_MA * self.props["C_PA"] * self.air_flow_fractions[i] *( self.T_SA -self.T_space_sp[i])
            if Q_sens_required < Q_system_max:
                vav_supply_fraction = 1.0
            else:
                vav_supply_fraction = Q_sens_required / Q_system_max
        else:
            vav_supply_fraction = 1.0
        return vav_supply_fraction
    
    def _get_Q_reheat_required(self, i, space):
        K_t,F_t = space.get_thermal_equation(False)
        T_flo = F_t/K_t
        if T_flo < self.T_space_sp[i]:
            Q_reheat =  K_t * self.T_space_sp[i] - F_t
        else:
            Q_reheat = 0
        return Q_reheat

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        self.variable("state").values[time_index] = self.state
        if self.state != 0 : # on
            self.variable("T_MA").values[time_index] = self.T_MA
            self.variable("T_MAwb").values[time_index] = self.T_MAwb
            m_supply = self.air_flow * self.rho_MA
            self.variable("m_air_flow").values[time_index] = m_supply
            for i in range(len(self.parameter("spaces").value)):
                m_i = self.air_flow * self.rho_MA * self.air_flow_fractions[i] * self.vav_supply_fraction[i]
                self.variable(f"m_air_flow_{i}").values[time_index] = m_i
                if self.is_reheat:
                    self.variable(f"Q_reheat_{i}").values[time_index] = self.Q_reheat[i]
                    self.variable(f"T_SA_{i}").values[time_index] = self.T_SA + self.Q_reheat[i]/(m_i * self.props["C_PA"])
            self.variable("outdoor_air_fraction").values[time_index] = self.F_OA
            self.variable("T_CA").values[time_index] = self.T_CA
            self.variable("w_CA").values[time_index] = self.w_CA
            self.variable("T_SA").values[time_index] = self.T_SA
            self.variable("w_SA").values[time_index] = self.w_SA
            self.variable("T_ZA").values[time_index] =self.T_ZA
            self.variable("T_RA").values[time_index] =self.T_RA
            self.variable("w_RA").values[time_index] =self.w_RA
            self.variable("F_load").values[time_index] = self.F_load
            self.variable("supply_fan_power").values[time_index] = self._get_fan_power("supply", self.F_load)
            self.variable("return_fan_power").values[time_index] = self._get_fan_power("return", self.F_load)          
            if self.state == 1 or self.state == 2: # Heating
                Q_sys = self.Q_coil
                self.variable("Q_sensible").values[time_index] = Q_sys
                self.variable("Q_total").values[time_index] = Q_sys
                self.variable("T_iw").values[time_index] = self.heating_water_temp
                self.variable("T_ow").values[time_index] = self.heating_water_temp - Q_sys/(self.heating_water_flow * self.props["RHOCP_W"](self.heating_water_temp))                    
                self.variable("T_ADP").values[time_index] = 0
                self.variable("epsilon").values[time_index] = self.epsilon
            elif self.state == -1 or self.state == -2: #Cooling
                Q_s = -self.Q_coil
                Q_l = -self.M_w * self.props["LAMBDA"]
                self.variable("Q_sensible").values[time_index] = Q_s
                self.variable("Q_latent").values[time_index] = Q_l
                self.variable("Q_total").values[time_index] = Q_s
                self.variable("T_iw").values[time_index] = self.cooling_water_temp
                self.variable("T_ow").values[time_index] = self.cooling_water_temp + (Q_s+Q_l)/(self.cooling_water_flow * self.props["RHOCP_W"](self.cooling_water_temp))                
                self.variable("T_ADP").values[time_index] = self.T_ADP
                self.variable("epsilon").values[time_index] = self.epsilon
                self.variable("epsilon_adp").values[time_index] = self.epsilon_adp
