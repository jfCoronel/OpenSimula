import math
from OpenSimula.Message import Message
from OpenSimula.components.Surface import Surface
from OpenSimula.Parameters import Parameter_component, Parameter_options, Parameter_boolean
from OpenSimula.visual_3D.Polygon_3D import Polygon_3D


class Solar_surface(Surface):
    def __init__(self, name, project):
        Surface.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Solar_surface"
        self.parameter("description").value = "Solar surface"
        self.add_parameter(Parameter_options("coordinate_system", "BUILDING", ["BUILDING", "GLOBAL"]))
        self.add_parameter(Parameter_component("building", "not_defined", ["Building"]))
        self.add_parameter(Parameter_boolean("cast_shadows", True))
        self.add_parameter(Parameter_boolean("calculate_solar_radiation", False))

        # Variables

    def check(self):
        errors = super().check()
        # Test building is defined
        if self.parameter("coordinate_system").value == "BUILDING" and self.parameter("building").value == "not_defined":
            msg = f"{self.parameter('name').value}, must define its building."
            errors.append(Message(msg, "ERROR"))
        return errors

    def get_building(self):
        if self.parameter("coordinate_system").value == "BUILDING":
            return self.parameter("building").component
        else:
            return None
        
     # ____________ pre_simulation ____________
    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        if self.parameter("calculate_solar_radiation").value:  
            self._file_met = self.project().parameter("simulation_file_met").component
            self._sunny_index_ = self.project().env_3D.get_sunny_index(self.parameter("name").value)
            self._albedo = self.project().parameter("albedo").value
            self._F_sky = (1 + math.sin(math.radians(self.parameter("altitude").value))) / 2


    def pre_iteration(self, time_i, date, daylight_saving):
        super().pre_iteration(time_i, date, daylight_saving)
        if self.parameter("calculate_solar_radiation").value:   
            # Meterological data
            hor_sol_dif = self._file_met.variable("sol_diffuse").values[time_i]
            hor_sol_dir = self._file_met.variable("sol_direct").values[time_i]

            # Diffuse solar radiation
            E_dif_sunny = self._file_met.solar_diffuse_rad(
                time_i,
                self.orientation_angle("azimuth", 0),
                self.orientation_angle("altitude", 0),
            )
            E_dif_sunny = E_dif_sunny + (1 - self._F_sky) * self._albedo * (hor_sol_dif + hor_sol_dir)
            self.variable("E_dif_sunny").values[time_i] = E_dif_sunny
            diffuse_sunny_fraction = self.project().env_3D.get_diffuse_sunny_fraction(self._sunny_index_)
            E_dif = E_dif_sunny * diffuse_sunny_fraction
            self.variable("E_dif").values[time_i] = E_dif
            # Direct solar radiation
            E_dir_sunny = self._file_met.solar_direct_rad(
                time_i,
                self.orientation_angle("azimuth", 0),
                self.orientation_angle("altitude", 0),
            )
            self.variable("E_dir_sunny").values[time_i] = E_dir_sunny
            E_dir = E_dir_sunny * self._calculate_direct_sunny_fraction_(time_i)
            self.variable("E_dir").values[time_i] = E_dir

    def _calculate_direct_sunny_fraction_(self, time_i):
        if self.project().parameter("shadow_calculation").value == "INSTANT":
            direct_sunny_fraction = self.project().env_3D.get_direct_sunny_fraction(
                self._sunny_index_
            )
        elif self.project().parameter("shadow_calculation").value == "INTERPOLATION":
            azi = self._file_met.variable("sol_azimuth").values[time_i]
            alt = self._file_met.variable("sol_altitude").values[time_i]
            if not math.isnan(alt):
                direct_sunny_fraction = (
                    self.project().env_3D.get_direct_interpolated_sunny_fraction(
                        self._sunny_index_, azi, alt
                    )
                )
            else:
                direct_sunny_fraction = 1
        elif self.project().parameter("shadow_calculation").value == "NO":
            direct_sunny_fraction = 1
        return direct_sunny_fraction

    def get_polygon_3D(self):
        if self.parameter("coordinate_system").value == "BUILDING":
           coord_system = "global"
        else:
           coord_system = "local"
        azimuth = self.orientation_angle("azimuth", 0, coord_system)
        altitude = self.orientation_angle("altitude", 0, coord_system)
        origin = self.get_origin(coord_system)
        pol_2D = self.get_polygon_2D()
        name = self.parameter("name").value
        shading = self.parameter("cast_shadows").value
        calculate_shadows = self.parameter("calculate_solar_radiation").value
        return Polygon_3D(
            name,
            origin,
            azimuth,
            altitude,
            pol_2D,
            color="cyan",
            shading=shading,
            calculate_shadows=calculate_shadows,
        )
