from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_component, Parameter_float
from OpenSimula.Variable import Variable
import numpy as np


class Space(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Space"
        self.parameter("description").value = "Indoor building space"
        # Parameters
        self.add_parameter(Parameter_component("space_type"))
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

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._space_type_comp_ = self.parameter("space_type").component
        self._area_ = self.parameter("floor_area").value
        self._volume_ = self.parameter("volume").value
        self._create_surfaces_list()
        self._calculate_area_list()

    def _create_surfaces_list(self):
        project_surfaces_list = self.project().component_list(type="Surface")
        self.surfaces_list = []
        for surface in project_surfaces_list:
            if surface.parameter("space").component == self or surface.parameter("adjacent_space").component == self:
                self.surfaces_list.append(surface)

    def _calculate_area_list(self):
        self.areas = []
        for surface in self.surfaces_list:
            self.areas.append(surface.parameter('area').value)

    def _calculate_form_factors(self):
        n = len(self.areas)
        total_area = sum(self.areas)
        self._ff_matrix = np.zeros((n, n))
        seven = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if (self.surfaces_list[i].parameter("azimuth").value == self.surfaces_list[j].parameter("azimuth").value
                        and self.surfaces_list[i].parameter("altitude").value == self.surfaces_list[j].parameter("altitude").value):
                    seven[i][j] = 0
                else:
                    seven[i][j] = 1
                self._ff_matrix[i][j] = seven[i][j]*self.area[j]/total_area
        # iteración
        EPSILON = 1.e-4
        N_MAX_ITER = 500
        n_iter = 0
        residuos = np.ones(n)
        while True:
            n_iter += 1
            resiTot=0
            for i in range(n):
                residuos[i]=1.
                for j in range(n):
                    residuos[i] -= self._ff_matrix[i][j]
            if (residuos[i]==0):
                residuos[i]=1.e-6
     if (fabs(resi[i])>epsilon)
     {
       noPasa ++;
       resiTot += fabs(resi[i]);
     }
   }
   // corregir la matriz
   if (noPasa)
   {
     for (i=0;i<n;i++)
       for (j=0;j<n;j++)
	 ff[i][j] *= 1+resi[i]*resi[j]*seven[i][j]/(fabs(resi[i])+fabs(resi[j]));
   }
   else
     break;

   if (nIter>nMaxIter) break;
 }

    def pre_iteration(self, time_index, date):
        super().pre_iteration(time_index, date)

        # People
        self.variable("people_convective").values[time_index] = self._area_ * \
            self._space_type_comp_.variable(
                "people_convective").values[time_index]
        self.variable("people_latent").values[time_index] = self._area_ * \
            self._space_type_comp_.variable("people_latent").values[time_index]
        self.variable("people_radiant").values[time_index] = self._area_ * \
            self._space_type_comp_.variable(
                "people_radiant").values[time_index]

        # Light
        self.variable("light_convective").values[time_index] = self._area_ * \
            self._space_type_comp_.variable(
                "light_convective").values[time_index]
        self.variable("light_radiant").values[time_index] = self._area_ * \
            self._space_type_comp_.variable("light_radiant").values[time_index]

        # Other gains
        self.variable("other_gains_convective").values[time_index] = self._area_ * \
            self._space_type_comp_.variable(
                "other_gains_convective").values[time_index]
        self.variable("other_gains_latent").values[time_index] = self._area_ * \
            self._space_type_comp_.variable(
                "other_gains_latent").values[time_index]
        self.variable("other_gains_radiant").values[time_index] = self._area_ * \
            self._space_type_comp_.variable(
                "other_gains_radiant").values[time_index]

        # Infiltration
        self.variable("infiltration_flow").values[time_index] = self._volume_ * \
            self._space_type_comp_.variable(
                "infiltration_rate").values[time_index]
