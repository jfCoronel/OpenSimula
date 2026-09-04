from opensimula.Component import Component
from opensimula.Message import Message
from opensimula.Parameters import Parameter_component, Parameter_float
from opensimula.Variable import Variable
from opensimula.Iterative_process import Iterative_process
import numpy as np
import psychrolib as sicro
import math


ANGLE_TOL = 1.0e-6  # degrees
FF_TOLERANCE = 1.0e-12
FF_ERROR_MAX = 1.0e-8
FF_N_MAX_ITER = 200
FF_N_SINKHORN = 10
FF_N_MAX_BACKTRACK = 30


class Space(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Space"
        self.parameter("description").value = "Indoor building space"
        # Parameters
        self.add_parameter(
            Parameter_component("spaces_type", "not_defined", ["Space_type"])
        )
        self.add_parameter(Parameter_component("building", "not_defined", ["Building"]))
        self.add_parameter(Parameter_float("floor_area", 1, "m²", min=0.0))
        self.add_parameter(Parameter_float("volume", 1, "m³", min=0.0))
        self.add_parameter(Parameter_float("furniture_weight", 10, "kg/m²", min=0.0))
        self.add_parameter(Parameter_float("convergence_DT", 0.01, "°C", min=0.0))
        self.add_parameter(Parameter_float("convergence_Dw", 0.1, "g/kg", min=0.0))

        # Variables
        self.add_variable(Variable("temperature", unit="°C"))
        self.add_variable(Variable("abs_humidity", unit="g/kg"))
        self.add_variable(Variable("rel_humidity", unit="%"))
        self.add_variable(Variable("people_convective", unit="W"))
        self.add_variable(Variable("people_radiant", unit="W"))
        self.add_variable(Variable("people_latent", unit="W"))
        self.add_variable(Variable("light_convective", unit="W"))
        self.add_variable(Variable("light_radiant", unit="W"))
        self.add_variable(Variable("other_gains_convective", unit="W"))
        self.add_variable(Variable("other_gains_radiant", unit="W"))
        self.add_variable(Variable("other_gains_latent", unit="W"))
        self.add_variable(Variable("solar_direct_gains", unit="W"))
        self.add_variable(Variable("infiltration_flow", unit="m³/s"))
        self.add_variable(Variable("surfaces_convective", unit="W"))
        self.add_variable(Variable("delta_int_energy", unit="W"))
        self.add_variable(Variable("infiltration_sensible_heat", unit="W"))
        self.add_variable(Variable("infiltration_latent_heat", unit="W"))
        self.add_variable(Variable("system_sensible_heat", unit="W"))
        self.add_variable(Variable("system_latent_heat", unit="W"))
        self.add_variable(Variable("u_system_sensible_heat", unit="W"))
        self.add_variable(Variable("u_system_latent_heat", unit="W"))

    def get_building(self):
        return self.parameter("building").component

    def check(self):
        errors = super().check()
        # Test building is defined
        if self.parameter("building").value == "not_defined":
            msg = f"{self.parameter('name').value}, must define its building."
            errors.append(Message(msg, "ERROR"))
        # Test space_type defined
        if self.parameter("spaces_type").value == "not_defined":
            msg = f"{self.parameter('name').value}, must define its Space_type."
            errors.append(Message(msg, "ERROR"))
        self._create_surfaces_list()
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        sicro.SetUnitSystem(sicro.SI)
        self._file_met = self.project().parameter("simulation_file_met").component
        self.props = self._sim_.props
        self._space_type_comp = self.parameter("spaces_type").component
        self._area = self.parameter("floor_area").value
        self._volume = self.parameter("volume").value
        self._m_furniture = self._area * self.parameter("furniture_weight").value
        self._Dt = self.project().parameter("time_step").value
        self._create_surfaces_list()  # surfaces, sides
        self._create_ff_matrix()  # ff_matrix
        self._create_dist_vectors()  # dsr_dist_vector, ig_dist_vector
        self.uncontrol_systems = []
        self.control_system = {
            "M_a": 0,
            "T_a": 0,
            "w_a": 0,
            "Q_s": 0,
            "M_w": 0,
        }  # M_a (kg/s), T_a (°C), w_a (g/kg), Q_s (W), M_w (g H2O/s)

    def _create_surfaces_list(self):
        self.surfaces = []
        self.sides = []
        # Exterior
        surfaces_list = self.project().component_list("Building_surface")
        for surface in surfaces_list:
            surface_type = surface.parameter("surface_type").value
            if surface_type == "EXTERIOR":
                if surface.get_space() == self:
                    self.surfaces.append(surface)
                    self.sides.append(1)
                    for opening in surface.openings:
                        self.surfaces.append(opening)
                        self.sides.append(1)
            elif surface_type == "UNDERGROUND":
                if surface.get_space() == self:
                    self.surfaces.append(surface)
                    self.sides.append(1)
            elif surface_type == "INTERIOR":
                if surface.get_space(0) == self:
                    self.surfaces.append(surface)
                    self.sides.append(0)
                    for opening in surface.openings:
                        self.surfaces.append(opening)
                        self.sides.append(0)
                elif surface.get_space(1) == self:
                    self.surfaces.append(surface)
                    self.sides.append(1)
                    for opening in surface.openings:
                        self.surfaces.append(opening)
                        self.sides.append(1)
            elif surface_type == "VIRTUAL":
                if surface.get_space(0) == self:
                    self.surfaces.append(surface)
                    self.sides.append(0)
                elif surface.get_space(1) == self:
                    self.surfaces.append(surface)
                    self.sides.append(1)

    def _coplanar(self, surf1, side1, surf2, side2):
        alt_1 = surf1.orientation_angle("altitude", side1)
        alt_2 = surf2.orientation_angle("altitude", side2)
        if not math.isclose(alt_1, alt_2, abs_tol=ANGLE_TOL):
            return False
        if math.isclose(abs(alt_1), 90, abs_tol=ANGLE_TOL):
            # Horizontal surfaces, its azimuth does not define the plane
            return True
        az_1 = surf1.orientation_angle("azimuth", side1)
        az_2 = surf2.orientation_angle("azimuth", side2)
        az_difference = (az_1 - az_2 + 180) % 360 - 180
        return math.isclose(az_difference, 0, abs_tol=ANGLE_TOL)

    def _create_ff_matrix(self):
        """View factors between the surfaces of the space.

        Starts from an area weighted base matrix, F_ij = A_j/A_total, zero
        between coplanar surfaces, and closes it with a symmetric scaling
        F_ij = x_i * base_ij * x_j. That scaling imposes at the same time
        closure, each row adds up to 1, and reciprocity, A_i*F_ij = A_j*F_ji.
        """
        n = len(self.surfaces)
        self.ff_matrix = np.zeros((n, n))
        if n == 0:
            return
        name = self.parameter("name").value
        areas = np.array([surf.area for surf in self.surfaces], dtype=float)
        if not np.all(np.isfinite(areas)) or np.any(areas <= 0):
            msg = f"{name}, all its surfaces must have a positive area to calculate the view factors."
            self._sim_.message(Message(msg, "ERROR"))
            return

        visibility = np.ones((n, n))
        for i in range(n):
            visibility[i][i] = 0
            for j in range(i + 1, n):
                if self._coplanar(
                    self.surfaces[i], self.sides[i], self.surfaces[j], self.sides[j]
                ):
                    visibility[i][j] = 0
                    visibility[j][i] = 0
        base_matrix = visibility * (areas / areas.sum())

        if not self._ff_matrix_is_solvable(base_matrix, areas, visibility, name):
            self.ff_matrix = self._normalize_ff_rows(base_matrix)
            return
        self.ff_matrix, error = self._scale_ff_matrix(base_matrix)
        if error > FF_ERROR_MAX:
            msg = f"{name}, the view factors could not be closed, maximum error: {error:.3e}. Reciprocity is dropped."
            self._sim_.message(Message(msg, "WARNING"))
            self.ff_matrix = self._normalize_ff_rows(base_matrix)

    def _ff_matrix_is_solvable(self, base_matrix, areas, visibility, name):
        """Closure and reciprocity can only be met together if every surface
        sees some other one and no coplanar group holds more than half of the
        area of the space."""
        blind = np.flatnonzero(base_matrix.sum(axis=1) == 0)
        if len(blind) > 0:
            surf_name = self.surfaces[blind[0]].parameter("name").value
            msg = f"{name}, {surf_name} does not see any other surface of the space."
            self._sim_.message(Message(msg, "WARNING"))
            return False
        n = len(areas)
        group = np.full(n, -1)
        n_group = 0
        for i in range(n):
            if group[i] < 0:
                group[(visibility[i] == 0) & (group < 0)] = n_group
                n_group += 1
        for k in range(n_group):
            area_group = areas[group == k].sum()
            if area_group > areas.sum() - area_group:
                msg = f"{name}, the surfaces of one of its planes hold more than half of the area of the space, its view factors cannot meet closure and reciprocity at the same time. Reciprocity is dropped."
                self._sim_.message(Message(msg, "WARNING"))
                return False
        return True

    def _scale_ff_matrix(self, base_matrix):
        """Symmetric scaling x_i*(base*x)_i = 1, biproportional (Sinkhorn)
        steps to globalize and then Newton over log(x)."""
        n = base_matrix.shape[0]

        def error(x):
            residue = x * (base_matrix @ x) - 1
            return np.abs(residue).max() if np.all(np.isfinite(residue)) else math.inf

        x = np.ones(n)
        err = error(x)
        for n_iter in range(FF_N_MAX_ITER):
            if err < FF_TOLERANCE or not math.isfinite(err):
                break
            base_x = base_matrix @ x
            biproportional = np.sqrt(x / base_x)
            if n_iter < FF_N_SINKHORN:
                x, err = biproportional, error(biproportional)
                continue
            # Newton over log(x), jacobian = I + diag(1/base_x)*base*diag(x)
            jacobian = np.eye(n) + base_matrix * x / base_x[:, None]
            try:
                step = np.linalg.solve(jacobian, -np.log(x * base_x))
            except np.linalg.LinAlgError:
                x, err = biproportional, error(biproportional)
                continue
            for _ in range(FF_N_MAX_BACKTRACK):  # line search
                x_new = x * np.exp(step)
                err_new = error(x_new)
                if err_new < err:
                    x, err = x_new, err_new
                    break
                step = step / 2
            else:
                x, err = biproportional, error(biproportional)
        return x[:, None] * base_matrix * x, err

    def _normalize_ff_rows(self, base_matrix):
        """Closure only, used when reciprocity cannot be met."""
        row_sums = base_matrix.sum(axis=1)[:, None]
        return np.divide(
            base_matrix,
            row_sums,
            out=np.zeros_like(base_matrix),
            where=row_sums > 0,
        )

    def _create_dist_vectors(self):  # W/m^2 for each surface
        n = len(self.surfaces)
        total_area = 0
        floor_area = 0
        for i in range(n):
            total_area += self.surfaces[i].area
            # Floor
            if self.surfaces[i].orientation_angle("altitude", self.sides[i]) == 90:
                floor_area += self.surfaces[i].area
        self.dsr_dist_vector = np.zeros(n)
        self.ig_dist_vector = np.zeros(n)
        for i in range(n):
            if floor_area > 0:
                # Floor
                if self.surfaces[i].orientation_angle("altitude", self.sides[i]) == 90:
                    self.dsr_dist_vector[i] = 1 / floor_area
                else:
                    0
            else:
                self.dsr_dist_vector[i] = 1 / total_area
            self.ig_dist_vector[i] = 1 / total_area

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        # self._first_iteration = True
        # People
        exp = self._space_type_comp.variable("people_convective").values[time_index]
        self.variable("people_convective").values[time_index] = self._area * exp
        exp = self._space_type_comp.variable("people_latent").values[time_index]
        self.variable("people_latent").values[time_index] = self._area * exp
        exp = self._space_type_comp.variable("people_radiant").values[time_index]
        self.variable("people_radiant").values[time_index] = self._area * exp
        # Light
        exp = self._space_type_comp.variable("light_convective").values[time_index]
        self.variable("light_convective").values[time_index] = self._area * exp
        exp = self._space_type_comp.variable("light_radiant").values[time_index]
        self.variable("light_radiant").values[time_index] = self._area * exp
        # Other gains
        exp = self._space_type_comp.variable("other_gains_convective").values[
            time_index
        ]
        self.variable("other_gains_convective").values[time_index] = self._area * exp
        exp = self._space_type_comp.variable("other_gains_latent").values[time_index]
        self.variable("other_gains_latent").values[time_index] = self._area * exp
        exp = self._space_type_comp.variable("other_gains_radiant").values[time_index]
        self.variable("other_gains_radiant").values[time_index] = self._area * exp
        # Infiltration
        exp = self._space_type_comp.variable("infiltration_rate").values[time_index]
        V_inf = self._volume * exp / 3600
        self.variable("infiltration_flow").values[time_index] = V_inf
        # Usar inicialmente el mismo sistema del instante anterior
        # Systems air flows
        self.uncontrol_systems = []
        self.control_system = {"M_a": 0, "T_a": 0, "w_a": 0, "Q_s": 0, "M_w": 0}
        # Initial values
        self._estimate_T_w(time_index)
        # Iterative Process
        self.itera_T = Iterative_process(
            self._T,
            tol=self.parameter("convergence_DT").value,
            n_ini_relax=3,
            rel_vel=0.8,
        )
        self.itera_w = Iterative_process(
            self._w,
            tol=self.parameter("convergence_Dw").value,
            n_ini_relax=3,
            rel_vel=0.8,
        )

        # Humidity balance
        self._K_hum = self.props["RHO_A"] * (self._volume / self._Dt + V_inf)
        self._F_hum = (
            self.variable("people_latent").values[time_index]
            + self.variable("other_gains_latent").values[time_index]
        ) / self.props["LAMBDA"]
        self._F_hum += (
            self.props["RHO_A"] * self._volume / self._Dt * self._w_pre
            + self.props["RHO_A"]
            * V_inf
            * self._file_met.variable("abs_humidity").values[time_index]
        )

    def _estimate_T_w(self, time_i):
        if time_i == 0:
            self._T_pre = self.get_building().parameter("initial_temperature").value
            self._w_pre = self.get_building().parameter("initial_humidity").value
        else:
            self._T_pre = self.variable("temperature").values[time_i - 1]
            self._w_pre = self.variable("abs_humidity").values[time_i - 1]
        self.variable("temperature").values[time_i] = self._T_pre
        self.variable("abs_humidity").values[time_i] = self._w_pre
        self._T = self._T_pre
        self._w = self._w_pre

    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)

        # Calculate temperature
        K_tot, F_tot = self.get_thermal_equation(True)
        T = F_tot / K_tot
        self.variable("temperature").values[time_index] = self.itera_T.estimate_next_x(
            T
        )

        # Calculate humidity
        K_hum, F_hum = self.get_humidity_equation(True)
        w = F_hum / K_hum
        if w < 0:
            w = 0
        if T > -100 and T < 100:  # Sicro limits
            max_hum = (
                sicro.GetHumRatioFromRelHum(T, 1, self.props["ATM_PRESSURE"]) * 1000
            )
            if w > max_hum:
                w = max_hum

        self.variable("abs_humidity").values[time_index] = self.itera_w.estimate_next_x(
            w
        )

        # Test convergence
        converged = self.itera_T.converged() and self.itera_w.converged()
        return converged

    def calculate_solar_direct(self, time_i):
        solar_gain = 0
        for surf in self.surfaces:
            if surf.parameter("type").value == "Opening":
                if surf.is_exterior():
                    solar_gain += surf.area * surf.variable("E_dir_tra").values[time_i]
        self.variable("solar_direct_gains").values[time_i] = solar_gain

    def update_K_F(self, K_F):
        self.K_F = K_F

    def _acumulate_u_systems(self):
        self._M_a_u_systems = 0
        self._M_T_a_u_systems = 0
        self._M_w_a_u_systems = 0
        self._Q_s_u_systems = 0
        self._M_w_u_systems = 0
        for system in self.uncontrol_systems:
            self._M_a_u_systems += system["M_a"]
            self._M_T_a_u_systems += system["M_a"] * system["T_a"]
            self._M_w_a_u_systems += system["M_a"] * system["w_a"]
            self._Q_s_u_systems += system["Q_s"]
            self._M_w_u_systems += system["M_w"]

    def get_thermal_equation(self, include_control_system):
        self._acumulate_u_systems()
        # F_OS may be updated by the building in each iteration
        F_tot = (
            self.K_F["F"]
            + self.K_F["F_OS"]
            + self._M_T_a_u_systems * self.props["C_PA"]
            + self._Q_s_u_systems
        )
        K_tot = self.K_F["K"] + self._M_a_u_systems * self.props["C_PA"]
        if include_control_system:
            K_tot += self.control_system["M_a"] * self.props["C_PA"]
            F_tot += (
                self.control_system["M_a"]
                * self.props["C_PA"]
                * self.control_system["T_a"]
                + self.control_system["Q_s"]
            )
        return (K_tot, F_tot)

    def get_humidity_equation(self, include_control_system):
        self._acumulate_u_systems()
        K_hum = self._K_hum + self._M_a_u_systems
        F_hum = self._F_hum + self._M_w_a_u_systems + self._M_w_u_systems
        if include_control_system:
            K_hum += self.control_system["M_a"]
            F_hum += (
                self.control_system["M_a"] * self.control_system["w_a"]
                + self.control_system["M_w"]
            )
        return (K_hum, F_hum)

    def get_Q_required(self, T_cool_sp, T_heat_sp):
        K_tot, F_tot = self.get_thermal_equation(False)
        T = F_tot / K_tot
        if T > T_cool_sp:
            return K_tot * T_cool_sp - F_tot
        elif T < T_heat_sp:
            return K_tot * T_heat_sp - F_tot
        else:
            return 0

    def get_M_required(self, HR_min, HR_max):
        K_hum, F_hum = self.get_humidity_equation(False)
        w = F_hum / K_hum
        if w < 0:
            w = 0
        hr = (
            sicro.GetRelHumFromHumRatio(self._T, w / 1000, self.props["ATM_PRESSURE"])
            * 100
        )
        if hr < HR_min:
            w_min = (
                sicro.GetHumRatioFromRelHum(
                    self._T, HR_min / 100, self.props["ATM_PRESSURE"]
                )
                * 1000
            )
            return K_hum * w_min - F_hum
        elif hr > HR_max:
            w_max = (
                sicro.GetHumRatioFromRelHum(
                    self._T, HR_max / 100, self.props["ATM_PRESSURE"]
                )
                * 1000
            )
            return K_hum * w_max - F_hum
        else:
            return 0

    def add_uncontrol_system(self, system_dic):
        # Delete if exist
        self.del_uncontrol_system(system_dic["name"])
        # Append
        self.uncontrol_systems.append(system_dic)

    def del_uncontrol_system(self, system_name):
        self.uncontrol_systems = [
            air for air in self.uncontrol_systems if air["name"] != system_name
        ]

    def set_control_system(self, system_dic):
        self.control_system = system_dic

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        self._T = self.variable("temperature").values[time_index]
        self._w = self.variable("abs_humidity").values[time_index]
        if self._T < 100:  # Sicro limit
            rh = (
                sicro.GetRelHumFromHumRatio(
                    self._T, self._w / 1000, self.props["ATM_PRESSURE"]
                )
                * 100
            )
            self.variable("rel_humidity").values[time_index] = rh
        self._calculate_heat_fluxes(time_index)

    def _calculate_heat_fluxes(self, time_i):
        V_inf = self.variable("infiltration_flow").values[time_i]
        T_ext = self._file_met.variable("temperature").values[time_i]
        w_ext = self._file_met.variable("abs_humidity").values[time_i]

        # Sensibles
        self.variable("delta_int_energy").values[time_i] = (
            (
                self._volume * self.props["RHO_A"] * self.props["C_PA"]
                + self._m_furniture * self.props["C_P_FURNITURE"]
            )
            * (self._T - self._T_pre)
            / self._Dt
        )
        self.variable("infiltration_sensible_heat").values[time_i] = (
            V_inf * self.props["RHO_A"] * self.props["C_PA"] * (T_ext - self._T)
        )
        self.variable("u_system_sensible_heat").values[time_i] = self.props["C_PA"] * (
            self._M_T_a_u_systems - self._M_a_u_systems * self._T
        )
        Q = (
            self.control_system["M_a"]
            * self.props["C_PA"]
            * (self.control_system["T_a"] - self._T)
            + self.control_system["Q_s"]
        )
        self.variable("system_sensible_heat").values[time_i] = Q

        Q_rest = (
            self.variable("delta_int_energy").values[time_i]
            - Q
            - self.variable("people_convective").values[time_i]
            - self.variable("light_convective").values[time_i]
            - self.variable("other_gains_convective").values[time_i]
            - self.variable("infiltration_sensible_heat").values[time_i]
            - self.variable("u_system_sensible_heat").values[time_i]
        )

        self.variable("surfaces_convective").values[time_i] = Q_rest

        # Latents
        self.variable("infiltration_latent_heat").values[time_i] = (
            V_inf * self.props["RHO_A"] * self.props["LAMBDA"] * (w_ext - self._w)
        )
        self.variable("u_system_latent_heat").values[time_i] = self.props["LAMBDA"] * (
            self._M_w_a_u_systems - self._M_a_u_systems * self._w
        )
        self.variable("system_latent_heat").values[time_i] = (
            self.control_system["M_a"]
            * self.props["LAMBDA"]
            * (self.control_system["w_a"] - self._w)
            + self.control_system["M_w"] * self.props["LAMBDA"]
        )
