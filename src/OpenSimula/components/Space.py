from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_component, Parameter_float
from OpenSimula.Variable import Variable
import numpy as np
import math


class Space(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Space"
        self.parameter("description").value = "Indoor building space"
        # Parameters
        self.add_parameter(Parameter_component("space_type", "not_defined"))
        self.add_parameter(Parameter_component("building", "not_defined"))
        self.add_parameter(Parameter_float("floor_area", 1, "m²", min=0.0))
        self.add_parameter(Parameter_float("volume", 1, "m³", min=0.0))

        # Variables
        self.add_variable(Variable("temperature", unit="°C"))
        self.add_variable(Variable("humidity", unit="g/kg"))
        self.add_variable(Variable("people_convective", unit="W"))
        self.add_variable(Variable("people_radiant", unit="W"))
        self.add_variable(Variable("people_latent", unit="W"))
        self.add_variable(Variable("light_convective", unit="W"))
        self.add_variable(Variable("light_radiant", unit="W"))
        self.add_variable(Variable("other_gains_convective", unit="W"))
        self.add_variable(Variable("other_gains_radiant", unit="W"))
        self.add_variable(Variable("other_gains_latent", unit="W"))
        self.add_variable(Variable("infiltration_flow", unit="m³/h"))

    def check(self):
        errors = super().check()
        # Test building is defined
        if self.parameter("building").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, must define its building.")
        # Test space_type defined
        if self.parameter("space_type").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, must define its Space_type.")
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._space_type_comp = self.parameter("space_type").component
        self._area = self.parameter("floor_area").value
        self._volume = self.parameter("volume").value
        self._create_surfaces_list()
        self._create_ff_matrix()
        self._create_dist_vectors()

    def _create_surfaces_list(self):
        project_surfaces_list = self.project().component_list(type="Surface")
        self._surfaces = []
        for surface in project_surfaces_list:
            if surface.parameter("space").component == self or surface.parameter("adjacent_space").component == self:
                adjacent = surface.parameter(
                    "adjacent_space").component == self
                if adjacent:
                    azimuth = surface.parameter("azimuth").value - 180
                    if azimuth < -180:
                        azimuth = azimuth + 360
                    altitude = surface.parameter("altitude").value - 180
                    if altitude < -90:
                        altitude = altitude + 180
                    rho_sw = surface.rho_sw()
                    tau_sw = surface.tau_sw()
                    alpha_sw = surface.alpha_sw()
                    rho_lw = surface.rho_lw()
                    tau_lw = surface.tau_lw()
                    alpha_lw = surface.alpha_lw()

                else:
                    azimuth = surface.parameter("azimuth").value
                    altitude = surface.parameter("altitude").value
                    rho_sw = surface.rho_sw(1)
                    tau_sw = surface.tau_sw(1)
                    alpha_sw = surface.alpha_sw(1)
                    rho_lw = surface.rho_lw(1)
                    tau_lw = surface.tau_lw(1)
                    alpha_lw = surface.alpha_lw(1)

                surface_dic = {"comp": surface,
                               "type": "Surface",
                               "area": surface.net_area,
                               "virtual": surface.parameter("virtual").value,
                               "azimuth": azimuth,
                               "altitude": altitude,
                               "rho_sw": rho_sw,
                               "tau_sw": tau_sw,
                               "alpha_sw": alpha_sw,
                               "rho_lw": rho_lw,
                               "tau_lw": tau_lw,
                               "alpha_lw": alpha_lw
                               }
                self._surfaces.append(surface_dic)
                for opening in surface._openings:
                    if adjacent:
                        rho_sw = opening["comp"].rho_sw()
                        tau_sw = opening["comp"].tau_sw()
                        alpha_sw = opening["comp"].alpha_sw()
                        rho_lw = opening["comp"].rho_lw()
                        tau_lw = opening["comp"].tau_lw()
                        alpha_lw = opening["comp"].alpha_lw()
                    else:
                        rho_sw = opening["comp"].rho_sw(1)
                        tau_sw = opening["comp"].tau_sw(1)
                        alpha_sw = opening["comp"].alpha_sw(1)
                        rho_lw = opening["comp"].rho_lw(1)
                        tau_lw = opening["comp"].tau_lw(1)
                        alpha_lw = opening["comp"].alpha_lw(1)
                    opening_dic = {"comp": opening["comp"],
                                   "type": "Opening",
                                   "area": opening["area"],
                                   "virtual": opening["virtual"],
                                   "azimuth": azimuth,
                                   "altitude": altitude,
                                   "rho_sw": rho_sw,
                                   "tau_sw": tau_sw,
                                   "alpha_sw": alpha_sw,
                                   "rho_lw": rho_lw,
                                   "tau_lw": tau_lw,
                                   "alpha_lw": alpha_lw
                                   }
                    self._surfaces.append(opening_dic)

    def _coplanar(self, surf1, surf2):
        if surf1["altitude"] == 90 and surf2["altitude"] == 90:
            return True
        elif surf1["altitude"] == -90 and surf2["altitude"] == -90:
            return True
        else:
            if surf1["altitude"] == surf2["altitude"] and surf1["azimuth"] == surf2["azimuth"]:
                return True
            else:
                return False

    def _create_ff_matrix(self):
        n = len(self._surfaces)
        total_area = 0
        for surf in self._surfaces:
            total_area += surf["area"]
        self._ff_matrix = np.zeros((n, n))
        seven = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if self._coplanar(self._surfaces[i], self._surfaces[j]):
                    seven[i][j] = 0
                else:
                    seven[i][j] = 1
                self._ff_matrix[i][j] = seven[i][j] * \
                    self._surfaces[j]["area"]/total_area
        # iteración
        EPSILON = 1.e-4
        N_MAX_ITER = 500
        n_iter = 0
        residuos = np.ones(n)
        while True:
            n_iter += 1
            residuo_tot = 0
            corregir = False
            for i in range(n):
                residuos[i] = 1.
                for j in range(n):
                    residuos[i] -= self._ff_matrix[i][j]
                if (residuos[i] == 0):
                    residuos[i] = EPSILON/100
                if (math.fabs(residuos[i]) > EPSILON):
                    corregir = True
                    residuo_tot += math.fabs(residuos[i])
            if corregir:
                for i in range(n):
                    for j in range(n):
                        self._ff_matrix[i][j] *= 1 + residuos[i]*residuos[j] * \
                            seven[i][j] / (math.fabs(residuos[i]) +
                                           math.fabs(residuos[j]))
            else:
                break
            if (n_iter > N_MAX_ITER):
                break

    def _create_dist_vectors(self):  # W/m^2 for each surface
        n = len(self._surfaces)
        total_area = 0
        floor_area = 0
        for surf in self._surfaces:
            total_area += surf["area"]
            if surf["altitude"] == 90:  # Floor
                floor_area += surf["area"]
        self._dsr_dist_vector = np.zeros(n)
        self._ig_dist_vector = np.zeros(n)
        for i in range(n):
            if floor_area > 0:
                if self._surfaces[i]["altitude"] == 90:  # Floor
                    self._dsr_dist_vector[i] = 1/floor_area
                else:
                    0
            else:
                self._dsr_dist_vector[i] = 1/total_area
            self._ig_dist_vector[i] = 1/total_area

    def pre_iteration(self, time_index, date):
        super().pre_iteration(time_index, date)

        # People
        self.variable("people_convective").values[time_index] = self._area * \
            self._space_type_comp.variable(
                "people_convective").values[time_index]
        self.variable("people_latent").values[time_index] = self._area * \
            self._space_type_comp.variable("people_latent").values[time_index]
        self.variable("people_radiant").values[time_index] = self._area * \
            self._space_type_comp.variable(
                "people_radiant").values[time_index]

        # Light
        self.variable("light_convective").values[time_index] = self._area * \
            self._space_type_comp.variable(
                "light_convective").values[time_index]
        self.variable("light_radiant").values[time_index] = self._area * \
            self._space_type_comp.variable("light_radiant").values[time_index]

        # Other gains
        self.variable("other_gains_convective").values[time_index] = self._area * \
            self._space_type_comp.variable(
                "other_gains_convective").values[time_index]
        self.variable("other_gains_latent").values[time_index] = self._area * \
            self._space_type_comp.variable(
                "other_gains_latent").values[time_index]
        self.variable("other_gains_radiant").values[time_index] = self._area * \
            self._space_type_comp.variable(
                "other_gains_radiant").values[time_index]

        # Infiltration
        self.variable("infiltration_flow").values[time_index] = self._volume * \
            self._space_type_comp.variable(
                "infiltration_rate").values[time_index]
