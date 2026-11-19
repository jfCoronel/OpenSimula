from opensimula.components.Thermal_zone import Thermal_zone
from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_float,
    Parameter_math_exp,
    Parameter_options,
    Parameter_variable_list,
)
from opensimula.Variable import Variable
import psychrolib as sicro

# Thermal mass of the zone by construction class, per m² of floor: heat capacity
# (J/(m²·K)) and area of the mass surfaces (m² per m² of floor), ISO 13790, table 12
CONSTRUCTIONS = {
    "VERY_LIGHT": (80e3, 2.5),
    "LIGHT": (110e3, 2.5),
    "MEDIUM": (165e3, 2.5),
    "HEAVY": (260e3, 3.0),
    "VERY_HEAVY": (370e3, 3.5),
}
H_MASS = 9.1  # W/(m²·K), heat transfer coefficient between the air and the mass surfaces
C_FURNITURE = 10e3  # J/(m²·K) of floor, heat capacity of the furniture (10 kg/m²)


class Load_space(Thermal_zone):
    """A zone defined by its loads instead of by its building.

    It takes the place of a Space in the air systems (HVAC_perfect_system,
    HVAC_DX_system, HVAC_SZW_system, HVAC_MZW_system), so that an installation
    can be simulated from precalculated load records: a column of a File_data,
    a schedule, a Calculator...

    The loads are the heat that keeps the zone at the reference temperature and
    humidity, with the same sign as the system_sensible_heat and
    system_latent_heat of a Space (positive heating / humidifying). The record
    already holds the dynamics of the building at constant temperature; when
    the systems do not supply that load, the zone departs from the reference
    following a model of two nodes, air and thermal mass, solved implicitly for
    any time step.

    The infiltration the record was calculated with (load_infiltration) is taken
    out of the loads at the reference conditions, and the simulated one
    (infiltration) is added at the actual temperature and humidity of the zone.
    """

    def __init__(self, name, project):
        Thermal_zone.__init__(self, name, project)
        self.parameter("type").value = "Load_space"
        self.parameter("description").value = "Zone defined by its load records"
        # Parameters
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("sensible_load", "0", "W"))
        self.add_parameter(Parameter_math_exp("latent_load", "0", "W"))
        self.add_parameter(Parameter_math_exp("reference_temperature", "24", "°C"))
        self.add_parameter(Parameter_math_exp("reference_humidity", "50", "%"))
        self.add_parameter(Parameter_math_exp("load_infiltration", "0.5", "1/h"))
        self.add_parameter(Parameter_math_exp("infiltration", "0.5", "1/h"))
        self.add_parameter(Parameter_float("floor_area", 100, "m²", min=0.001))
        self.add_parameter(Parameter_float("height", 2.7, "m", min=0.001))
        self.add_parameter(
            Parameter_options("construction", "MEDIUM", list(CONSTRUCTIONS) + ["CUSTOM"])
        )
        self.add_parameter(Parameter_float("custom_mass_capacity", 165, "kJ/(m²·K)", min=0))
        self.add_parameter(Parameter_float("custom_mass_area", 2.5, "m²/m²", min=0))
        self.add_parameter(Parameter_float("envelope_conductance", 1.0, "W/(m²·K)", min=0))
        self.add_parameter(Parameter_float("convergence_DT", 0.01, "°C", min=0.0))
        self.add_parameter(Parameter_float("convergence_Dw", 0.01, "g/kg", min=0.0))

        # Variables
        self.add_variable(Variable("temperature", unit="°C"))
        self.add_variable(Variable("abs_humidity", unit="g/kg"))
        self.add_variable(Variable("rel_humidity", unit="%"))
        self.add_variable(Variable("mass_temperature", unit="°C"))
        self.add_variable(Variable("reference_temperature", unit="°C"))
        self.add_variable(Variable("sensible_load", unit="W"))
        self.add_variable(Variable("latent_load", unit="W"))
        self.add_variable(Variable("infiltration_flow", unit="m³/s"))
        self.add_variable(Variable("system_sensible_heat", unit="W"))
        self.add_variable(Variable("system_latent_heat", unit="W"))
        self.add_variable(Variable("u_system_sensible_heat", unit="W"))
        self.add_variable(Variable("u_system_latent_heat", unit="W"))
        self.add_variable(Variable("unmet_sensible_heat", unit="W"))

    def check(self):
        errors = super().check()
        if self.project().parameter("simulation_file_met").value == "not_defined":
            msg = f"{self.parameter('name').value}, file_met must be defined in the project 'simulation_file_met'."
            errors.append(Message(msg, "ERROR"))
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        sicro.SetUnitSystem(sicro.SI)
        self.props = self._sim_.props
        self._file_met = self.project().parameter("simulation_file_met").component
        self._Dt = self.project().parameter("time_step").value
        area = self.parameter("floor_area").value
        self._volume = area * self.parameter("height").value
        construction = self.parameter("construction").value
        if construction == "CUSTOM":
            c_m = self.parameter("custom_mass_capacity").value * 1000
            a_m = self.parameter("custom_mass_area").value
        else:
            c_m, a_m = CONSTRUCTIONS[construction]
        rho_cp_V = self.props["RHO_A"] * self.props["C_PA"] * self._volume
        self._C_a = rho_cp_V + C_FURNITURE * area  # J/K
        self._C_m = c_m * area  # J/K
        self._H_am = H_MASS * a_m * area  # W/K
        U = self.parameter("envelope_conductance").value * area
        self._H_ao = U / 2  # W/K, windows: air to outdoor
        self._H_mo = U / 2  # W/K, opaque: mass to outdoor
        # deviations from the reference at the end of the previous step
        self._theta_pre = 0.0
        self._theta_m_pre = 0.0
        self._reset_systems_()

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        var_dic = self.get_parameter_variable_dictionary(time_index)
        atm_p = self.props["ATM_PRESSURE"]
        rho = self.props["RHO_A"]
        T_ext = self._file_met.variable("temperature").values[time_index]
        w_ext = self._file_met.variable("abs_humidity").values[time_index]
        self._T_ref = self.parameter("reference_temperature").evaluate(var_dic)
        RH_ref = self.parameter("reference_humidity").evaluate(var_dic)
        self._w_ref = sicro.GetHumRatioFromRelHum(self._T_ref, RH_ref / 100, atm_p) * 1000
        n_load = self.parameter("load_infiltration").evaluate(var_dic)
        n = self.parameter("infiltration").evaluate(var_dic)
        V_load = self._volume * n_load / 3600  # m³/s
        V_inf = self._volume * n / 3600
        self.variable("reference_temperature").values[time_index] = self._T_ref
        self.variable("infiltration_flow").values[time_index] = V_inf

        # Loads without the infiltration they were calculated with
        H_load = rho * self.props["C_PA"] * V_load
        Q_zone = self.parameter("sensible_load").evaluate(var_dic) - H_load * (self._T_ref - T_ext)
        # vapour released in the zone (g/s): the latent load is what the system supplies
        M_zone = (
            -self.parameter("latent_load").evaluate(var_dic) / self.props["LAMBDA"]
            - rho * V_load * (w_ext - self._w_ref)
        )
        # Loads at the reference conditions with the simulated infiltration
        H_inf = rho * self.props["C_PA"] * V_inf
        self._Q_load = Q_zone + H_inf * (self._T_ref - T_ext)
        self.variable("sensible_load").values[time_index] = self._Q_load
        self.variable("latent_load").values[time_index] = -self.props["LAMBDA"] * (
            M_zone + rho * V_inf * (w_ext - self._w_ref)
        )

        # Thermal balance, two nodes, in deviations theta = T - T_ref:
        #   C_a/Dt·(th - th_pre) = Q_sys - Q_zone - H_inf·(T - T_ext) - H_ao·th - H_am·(th - th_m)
        #   C_m/Dt·(th_m - th_m_pre) = H_am·(th - th_m) - H_mo·th_m
        # the mass node, th_m = a + b·th, is eliminated: K·T = F + Q_sys
        D = self._C_m / self._Dt + self._H_am + self._H_mo
        self._a = self._C_m / self._Dt * self._theta_m_pre / D
        self._b = self._H_am / D
        G = self._C_a / self._Dt + self._H_ao + self._H_am * (1 - self._b)
        self._K = G + H_inf
        self._F = (
            G * self._T_ref
            + self._C_a / self._Dt * self._theta_pre
            + self._H_am * self._a
            - Q_zone
            + H_inf * T_ext
        )

        # Humidity balance (g/s): rho·V/Dt·(w - w_pre) = M_zone + rho·V_inf·(w_ext - w) + systems
        self._w_pre = self._w_ref if time_index == 0 else self.variable("abs_humidity").values[time_index - 1]
        self._K_hum = rho * (self._volume / self._Dt + V_inf)
        self._F_hum = rho * self._volume / self._Dt * self._w_pre + M_zone + rho * V_inf * w_ext

        # First estimate: the deviation of the previous step
        self._T = self._T_ref + self._theta_pre
        self._w = self._w_pre
        self.variable("temperature").values[time_index] = self._T
        self.variable("abs_humidity").values[time_index] = self._w
        self._reset_systems_()
        self._create_iterative_processes_()

    def _zone_thermal_equation_(self):
        return (self._K, self._F)

    def _zone_humidity_equation_(self):
        return (self._K_hum, self._F_hum)

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        self._calculate_system_heat_(time_index)
        theta = self._T - self._T_ref
        theta_m = self._a + self._b * theta
        self._theta_pre = theta
        self._theta_m_pre = theta_m
        self.variable("mass_temperature").values[time_index] = self._T_ref + theta_m
        self.variable("unmet_sensible_heat").values[time_index] = (
            self._Q_load
            - self.variable("system_sensible_heat").values[time_index]
            - self.variable("u_system_sensible_heat").values[time_index]
        )
