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

    def building(self):
        return self.parameter("building").component

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
        self._file_met = self.building().parameter("file_met").component
        self._space_type_comp = self.parameter("space_type").component
        self._area = self.parameter("floor_area").value
        self._volume = self.parameter("volume").value
        self._create_surfaces_list()
        self._create_ff_matrix()
        self._create_dist_vectors()

    def _create_surfaces_list(self):
        self.surfaces = []
        self.sides = []
        # Exterior
        project_exterior_surfaces_list = self.project(
        ).component_list(type="Exterior_surface")
        for surface in project_exterior_surfaces_list:
            if surface.parameter("space").component == self:
                self.surfaces.append(surface)
                self.sides.append(1)
                for opening in surface.openings:
                    self.surfaces.append(opening)
                    self.sides.append(1)

        # Underground
        project_underground_surfaces_list = self.project(
        ).component_list(type="Underground_surface")
        for surface in project_underground_surfaces_list:
            if surface.parameter("space").component == self:
                self.surfaces.append(surface)
                self.sides.append(1)

        # Interior
        project_interior_surfaces_list = self.project(
        ).component_list(type="Interior_surface")
        for surface in project_interior_surfaces_list:
            if surface.parameter("spaces").component[0] == self:
                self.surfaces.append(surface)
                self.sides.append[0]
            elif surface.parameter("spaces").component[1] == self:
                self.surfaces.append(surface)
                self.sides.append[1]

    def _coplanar(self, surf1, surf2):
        if surf1.parameter("altitude").value == 90 and surf2.parameter("altitude").value == 90:
            return True
        elif surf1.parameter("altitude").value == -90 and surf2.parameter("altitude").value == -90:
            return True
        else:
            if surf1.parameter("altitude").value == surf2.parameter("altitude").value and surf1.parameter("azimuth").value == surf2.parameter("azimuth").value:
                return True
            else:
                return False

    def _create_ff_matrix(self):
        n = len(self.surfaces)
        total_area = 0
        for surf in self.surfaces:
            total_area += surf.net_area()
        self._ff_matrix = np.zeros((n, n))
        seven = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if self._coplanar(self.surfaces[i], self.surfaces[j]):
                    seven[i][j] = 0
                else:
                    seven[i][j] = 1
                self._ff_matrix[i][j] = seven[i][j] * \
                    self.surfaces[j].net_area()/total_area
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
        n = len(self.surfaces)
        total_area = 0
        floor_area = 0
        for surf in self.surfaces:
            total_area += surf.net_area()
            if surf.parameter("altitude").value == -90:  # Floor
                floor_area += surf.net_area()
        self._dsr_dist_vector = np.zeros(n)
        self._ig_dist_vector = np.zeros(n)
        for i in range(n):
            if floor_area > 0:
                if self.surfaces[i].parameter("altitude").value == -90:  # Floor
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
