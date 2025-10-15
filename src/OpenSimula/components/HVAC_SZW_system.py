from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_component,
    Parameter_float,
    Parameter_variable_list,
    Parameter_math_exp,
    Parameter_options,
)
from opensimula.Component import Component
from opensimula.Variable import Variable
import psychrolib as sicro


class HVAC_SZW_system(Component):  # HVAC Single Zone Water system
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_SZW_system"
        self.parameter("description").value = "HVAC Single Zone Water system"
        self.add_parameter(
            Parameter_component("space", "not_defined", ["Space"])
        )  # Space
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
        self.add_parameter(Parameter_float("return_air_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_math_exp("outdoor_air_fraction", "0", "frac"))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("heating_setpoint", "20", "°C"))
        self.add_parameter(Parameter_math_exp("cooling_setpoint", "25", "°C"))
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
        self.add_variable(Variable("m_return_air_flow", unit="kg/s"))
        self.add_variable(Variable("T_SA", unit="°C"))
        self.add_variable(Variable("w_SA", unit="g/kg"))
        self.add_variable(Variable("T_CA", unit="°C"))
        self.add_variable(Variable("w_CA", unit="g/kg"))
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
        self.add_variable(Variable("T_ADP", unit="°C"))
        self.add_variable(Variable("T_RA", unit="°C"))  # Return air temperature

    def check(self):
        errors = super().check()
        # Test space defined
        if self.parameter("space").value == "not_defined":
            msg = f"{self.parameter('name').value}, must define its space."
            errors.append(Message(msg, "ERROR"))
        # Test coil defined
        if (
            self.parameter("cooling_coil").value == "not_defined"
            and self.parameter("heating_coil").value == "not_defined"
        ):
            msg = f"{self.parameter('name').value}, must define one coil equipment."
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
        super().pre_simulation(n_time_steps, delta_t)
        # Sicro
        sicro.SetUnitSystem(sicro.SI)
        self.props = self._sim_.props
        self.file_met = self.project().parameter("simulation_file_met").component

        # Parameters
        self.space = self.parameter("space").component
        self.c_coil = self.parameter("cooling_coil").component
        self.h_coil = self.parameter("heating_coil").component
        self.supply_fan = self.parameter("supply_fan").component
        self.return_fan = self.parameter("return_fan").component
        self.air_flow = self.parameter("air_flow").value
        self.return_air_flow = self.parameter("return_air_flow").value

        # Water flows and temperatures
        self.cooling_water_flow = self.parameter("cooling_water_flow").value
        self.heating_water_flow = self.parameter("heating_water_flow").value
        if self.c_coil:
            self.cooling_F_water = (
                self.cooling_water_flow
                / self.c_coil.parameter("nominal_cooling_water_flow").value
            )
        if self.h_coil:
            self.heating_F_water = (
                self.heating_water_flow
                / self.h_coil.parameter("nominal_heating_water_flow").value
            )
        self.cooling_water_temp = self.parameter("inlet_cooling_water_temp").value
        self.heating_water_temp = self.parameter("inlet_heating_water_temp").value
        # Fan operation
        self.fan_operation = self.parameter("fan_operation").value
        # adp model
        self.water_flow_control = self.parameter("water_flow_control").value

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
        self.T_heat_sp = self.parameter("heating_setpoint").evaluate(var_dic)
        self.variable("heating_setpoint").values[time_index] = self.T_heat_sp
        self.T_cool_sp = self.parameter("cooling_setpoint").evaluate(var_dic)
        self.variable("cooling_setpoint").values[time_index] = self.T_cool_sp
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
        # Initial mass flows
        self.m_air_supply = self.air_flow * self.props["RHO_A"]
        if self.return_fan is None:  # No return fan
            self.v_air_return = self.air_flow * (1 - self.F_OA)
        else:  # Return fan
            self.v_air_return = self.return_air_flow

    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)
        if self.on_off:
            self._calculate_return_air(time_index)
            self._calculate_required_Q()
            if self.parameter("economizer").value != "NO":
                self._simulate_economizer()  # Calculation of new F_OA
                self._calculate_required_Q()
            self._calculate_mixed_air()
            self._simulate_system()
            self._update_supply_mass_flow()
            self._send_air_to_space()
        return True

    def _calculate_return_air(self, time_index):
        self.T_ZA = self.space.variable("temperature").values[time_index]
        self.w_ZA = self.space.variable("abs_humidity").values[time_index]
        rho_ZA = 1 / sicro.GetMoistAirVolume(
            self.T_ZA, self.w_ZA / 1000, self.props["ATM_PRESSURE"]
        )
        self.w_RA = self.w_ZA
        self.m_air_return = self.v_air_return * rho_ZA
        if self.return_fan is None:  # No return fan
            self.Q_return_fan_required = 0
            self.T_RA = self.T_ZA
        else:
            Q_return_fan = self._get_fan_power("return", self.F_load)
            self.Q_return_fan_required = (
                Q_return_fan * self.m_air_supply * (1 - self.F_OA) / self.m_air_return
            )
            self.T_RA = self.T_ZA + Q_return_fan / (
                self.m_air_return * self.props["C_PA"]
            )

    def _calculate_required_Q(self):
        K_t, F_t = self.space.get_thermal_equation(False)
        Q_supply_fan = self._get_fan_power("supply", self.F_load)
        m_cp_oa = self.m_air_supply * self.F_OA * self.props["C_PA"]
        K_ts = K_t + m_cp_oa
        F_ts = F_t + m_cp_oa * self.T_OA + Q_supply_fan + self.Q_return_fan_required
        T_flo = F_ts / K_ts
        if T_flo > self.T_cool_sp:
            self.Q_required = K_ts * self.T_cool_sp - F_ts
        elif T_flo < self.T_heat_sp:
            self.Q_required = K_ts * self.T_heat_sp - F_ts
        else:
            self.Q_required = 0
        if abs(self.Q_required) < 0.0001:  # Problems with convergence
            self.Q_required = 0

    def _get_fan_power(self, fan, F_load):
        if fan == "supply":
            if self.fan_operation == "CONTINUOUS":
                return self.supply_fan.get_power(self.air_flow)
            elif self.fan_operation == "CYCLING":
                return self.supply_fan.get_power(self.air_flow) * F_load
        elif fan == "return":
            if self.return_fan is None:  # No return fan
                return 0
            else:
                if self.fan_operation == "CONTINUOUS":
                    return self.return_fan.get_power(self.return_air_flow)
                elif self.fan_operation == "CYCLING":
                    return self.return_fan.get_power(self.return_air_flow) * F_load

    def _calculate_mixed_air(self):
        # Mixed air
        self.T_MA, self.w_MA, self.T_MAwb = self._mix_air(
            self.F_OA, self.T_OA, self.w_OA, self.T_RA, self.w_RA
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
                mrhocp = self.m_air_supply * self.props["C_PA"]
                Q_rest_oa = mrhocp * (1 - self.F_OA) * (self.T_OA - self.T_ZA)  
                if Q_rest_oa < self.Q_required:
                    self.F_OA += self.Q_required / (mrhocp * (self.T_OA - self.T_ZA))
                    self.Q_required = 0
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
            self.Q_eq = self._get_fan_power("supply", 0) + self.Q_return_fan_required
            self.M_w = 0

    def _simulate_heating(self):
        capacity, self.epsilon = self.h_coil.get_heating_capacity(
            self.T_MA,
            self.T_MAwb,
            self.heating_water_temp,
            self.air_flow,
            self.heating_water_flow,
        )
        self.M_w = 0  # No latent load in heating
        self.w_CA = self.w_MA
        # Q_required is only the coil capacity
        if capacity < self.Q_required:  # Coil capacity is not enough
            self.F_load = 1
            self.Q_coil = capacity
            self.Q_eq = (
                capacity + self._get_fan_power("supply", 1) + self.Q_return_fan_required
            )
            self.state = 2
        else:
            self.Q_coil = self.Q_required
            self.F_load = self.Q_coil / capacity
            self.Q_eq = (
                self.Q_required
                + self._get_fan_power("supply", self.F_load)
                + self.Q_return_fan_required
            )
            self.state = 1
        self.T_CA = self.T_MA + self.Q_coil / (self.m_air_supply * self.props["C_PA"])

    def _simulate_cooling(self):
        capacity_sen, capacity_lat, self.T_ADP, self.epsilon, self.epsilon_adp = (
            self.c_coil.get_cooling_capacity(
                self.T_MA,
                self.T_MAwb,
                self.cooling_water_temp,
                self.air_flow,
                self.cooling_water_flow,
            )
        )
        Q_required = -self.Q_required
        # Q_required is only the coil capacity
        if capacity_sen < Q_required:  # Coil capacity is not enough
            self.state = -2
            self.F_load = 1
            self.Q_coil = -capacity_sen
            self.T_CA = self.T_MA + self.Q_coil / (
                self.m_air_supply * self.props["C_PA"]
            )
            self.Q_eq = (
                self._get_fan_power("supply", 1)
                + self.Q_return_fan_required
                - capacity_sen
            )
            self.M_w = -(capacity_lat) / self.props["LAMBDA"]
        else:
            self.state = -1
            self.Q_coil = -Q_required
            self.F_load = Q_required / capacity_sen
            self.Q_eq = (
                -Q_required
                + self._get_fan_power("supply", self.F_load)
                + self.Q_return_fan_required
            )
            self.T_CA = self.T_MA + self.Q_coil / (
                self.m_air_supply * self.props["C_PA"]
            )
            if self.water_flow_control == "ON_OFF":
                self.M_w = -(capacity_lat * self.F_load) / self.props["LAMBDA"]
            elif self.water_flow_control == "PROPORTIONAL":
                Q_lat, self.T_ADP, self.epsilon_adp = (
                    self.c_coil.get_latent_cooling_load(
                        self.T_MA,
                        self.T_MAwb,
                        self.cooling_water_temp,
                        self.air_flow,
                        self.cooling_water_flow,
                        self.T_CA,
                    )
                )
                self.M_w = -Q_lat / self.props["LAMBDA"]
        self.w_CA = self.M_w / self.m_air_supply + self.w_MA

    def _update_supply_mass_flow(self):
        # Fan inlet
        rho_CA = 1 / sicro.GetMoistAirVolume(
            self.T_CA, self.w_CA / 1000, self.props["ATM_PRESSURE"]
        )
        self.m_air_supply = self.air_flow * rho_CA

    def _send_air_to_space(self):
        air_flow = {
            "M_a": self.m_air_supply * self.F_OA,
            "T_a": self.T_OA,
            "w_a": self.w_OA,
            "Q_s": self.Q_eq,
            "M_w": self.M_w,
        }
        self.space.set_control_system(air_flow)

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        self.variable("state").values[time_index] = self.state
        if self.state != 0:  # on
            self.variable("T_MA").values[time_index] = self.T_MA
            self.variable("T_MAwb").values[time_index] = self.T_MAwb
            self.variable("m_air_flow").values[time_index] = self.m_air_supply
            self.variable("m_return_air_flow").values[time_index] = self.m_air_return
            self.variable("outdoor_air_fraction").values[time_index] = self.F_OA
            # Density of air at the fan inlet
            self.variable("T_CA").values[time_index] = self.T_CA
            self.variable("w_CA").values[time_index] = self.w_CA
            self.variable("T_SA").values[time_index] = (
                self._get_fan_power("supply", self.F_load)
                / (self.m_air_supply * self.props["C_PA"])
                + self.T_CA
            )
            self.variable("w_SA").values[time_index] = self.w_CA
            self.variable("T_RA").values[time_index] = self.T_RA
            self.variable("F_load").values[time_index] = self.F_load
            self.variable("supply_fan_power").values[time_index] = self._get_fan_power(
                "supply", self.F_load
            )
            self.variable("return_fan_power").values[time_index] = self._get_fan_power(
                "return", self.F_load
            )
            if self.state == 1 or self.state == 2:  # Heating
                Q_sys = self.Q_coil
                self.variable("Q_sensible").values[time_index] = Q_sys
                self.variable("Q_total").values[time_index] = Q_sys
                self.variable("T_iw").values[time_index] = self.heating_water_temp
                self.variable("T_ow").values[time_index] = (
                    self.heating_water_temp
                    - Q_sys
                    / (
                        self.heating_water_flow
                        * self.props["RHOCP_W"](self.heating_water_temp)
                    )
                )
                self.variable("T_ADP").values[time_index] = 0
                self.variable("epsilon").values[time_index] = self.epsilon
            elif self.state == -1 or self.state == -2:  # Cooling
                Q_s = -self.Q_coil
                Q_l = -self.M_w * self.props["LAMBDA"]
                self.variable("Q_sensible").values[time_index] = Q_s
                self.variable("Q_latent").values[time_index] = Q_l
                self.variable("Q_total").values[time_index] = Q_s
                self.variable("T_iw").values[time_index] = self.cooling_water_temp
                self.variable("T_ow").values[time_index] = self.cooling_water_temp + (
                    Q_s + Q_l
                ) / (
                    self.cooling_water_flow
                    * self.props["RHOCP_W"](self.cooling_water_temp)
                )
                self.variable("T_ADP").values[time_index] = self.T_ADP
                self.variable("epsilon").values[time_index] = self.epsilon
                self.variable("epsilon_adp").values[time_index] = self.epsilon_adp
