import math
import datetime as dt
from opensimula.Component import Component
from opensimula.parameters import Parameter_string, Parameter_component
from opensimula.variables import Variable


class Outdoor(Component):
    def __init__(self):
        Component.__init__(self)
        self.parameter["type"].value = "Outdoor"
        self.parameter["name"].value = "Outdoor_x"
        self.add_parameter(
            Parameter_string("description", "Outdoor zone from a meteorological file")
        )
        self.add_parameter(Parameter_component("meteo_file", "not_defined"))

    def check(self):
        #
        self.parameter["meteo_file"].findComponent()
        if self.parameter["meteo_file"].component == None:
            self.message(
                "Error in component: "
                + self.parameter["name"].value
                + ", type: "
                + self.parameter["type"].value
            )
            self.message(
                "   meteo_file: "
                + self.parameter["meteo_file"].value
                + " component not found"
            )
            return 1
        else:
            return 0

    def pre_simulation(self, n_time_steps):
        self.latitude = self.parameter["meteo_file"].component.latitude
        self.longitude = self.parameter["meteo_file"].component.longitude
        self.altitude = self.parameter["meteo_file"].component.altitude
        self.reference_time_longitude = self.parameter[
            "meteo_file"
        ].component.reference_time_longitude
        self.add_variable(Variable("temperature", n_time_steps, unit="°C"))
        self.add_variable(Variable("sky_temperature", n_time_steps, unit="°C"))
        self.add_variable(Variable("abs_humidity", n_time_steps, unit="g/kg"))
        self.add_variable(Variable("sol_direct", n_time_steps, unit="W/m²"))
        self.add_variable(Variable("sol_diffuse", n_time_steps, unit="W/m²"))
        self.add_variable(Variable("wind_speed", n_time_steps, unit="m/s"))
        self.add_variable(Variable("wind_direction", n_time_steps, unit="°"))
        self.add_variable(Variable("sol_azimut", n_time_steps, unit="°"))
        self.add_variable(Variable("sol_altitude", n_time_steps, unit="°"))

    def pre_iteration(self, time_index, date):
        values = self.parameter["meteo_file"].component.get_instant_values(date)
        self.variable["temperature"].array[time_index] = values["temperature"]
        self.variable["sky_temperature"].array[time_index] = values["sky_temperature"]
        self.variable["abs_humidity"].array[time_index] = values["abs_humidity"] * 1000
        self.variable["sol_direct"].array[time_index] = values["sol_direct"]
        self.variable["sol_diffuse"].array[time_index] = values["sol_diffuse"]
        self.variable["wind_speed"].array[time_index] = values["wind_speed"]
        self.variable["wind_direction"].array[time_index] = values["wind_direction"]
        azi, alt = self.solar_pos(date)
        self.variable["sol_azimut"].array[time_index] = azi
        self.variable["sol_altitude"].array[time_index] = alt

    def iteration(self, time_index, date):
        return True

    def _solar_hour_(self, datetime):  # Hora solar
        day = datetime.timetuple().tm_yday  # Día del año
        hours = (
            datetime.hour + datetime.minute / 60 + datetime.second / 3600
        )  # hora local

        daylight_saving = (
            hours
            + (day - 1) * 24
            - (datetime.timestamp() - dt.datetime(datetime.year, 1, 1).timestamp())
            / 3600
        )
        # Ecuación del tiempo en minutos Duffie and Beckmann
        B = math.radians((day - 1) * 360 / 365)
        ecuacion_tiempo = 229.2 * (
            0.000075
            + 0.001868 * math.cos(B)
            - 0.032077 * math.sin(B)
            - 0.014615 * math.cos(2 * B)
            - 0.04089 * math.sin(2 * B)
        )
        longitude_correction = (self.reference_time_longitude - self.longitude) * 1 / 15
        hours += ecuacion_tiempo / 60 - daylight_saving - longitude_correction
        return hours

    def solar_pos(self, datetime):
        """Solar position

        Args:
            datetime (datetime): local time

        Returns:
            (number, number): (solar azimut, solar altitude)
        """
        solar_hour = self._solar_hour_(datetime)
        sunrise, sunset = self.sunrise_sunset(datetime)
        if solar_hour < sunrise or solar_hour > sunset:
            return (0.0, 0.0)
        else:
            cs, cw, cz = self._solar_pos_cos_(datetime)
            alt = math.atan(cz / math.sqrt(1.0 - cz**2))
            aux = cw / math.cos(alt)
            azi = 0.0
            if aux == -1.0:  # justo Este
                azi = -math.pi / 2
            elif aux == 1.0:  # justo Oeste
                azi = math.pi / 2
            else:
                azi = math.atan(aux / math.sqrt(1 - aux**2))
                if azi < 0:
                    if cs < 0:
                        azi = -math.pi - azi
                else:
                    if cs < 0:
                        azi = math.pi - azi
            return (azi * 180 / math.pi, alt * 180 / math.pi)

    def _solar_pos_cos_(self, datetime):
        """Solar position cosines

        Args:
            datetime (datetime): local time

        Returns:
            (number, number, number): (cos south, cost west, cos z)
        """
        solar_hour = self._solar_hour_(datetime)
        sunrise, sunset = self.sunrise_sunset(datetime)
        if solar_hour < sunrise or solar_hour > sunset:
            return (0.0, 0.0, 1.0)
        else:
            day = datetime.timetuple().tm_yday  # Día del año
            declina = math.radians(23.45 * math.sin(2 * math.pi * (284 + day) / 365))
            solar_angle = math.radians(15 * (solar_hour - 12))
            lat_radians = math.radians(self.latitude)

            cz = math.sin(lat_radians) * math.sin(declina) + math.cos(
                lat_radians
            ) * math.cos(declina) * math.cos(solar_angle)
            cw = math.cos(declina) * math.sin(solar_angle)
            aux = 1.0 - cw**2 - cz**2
            if aux > 0:
                cs = math.sqrt(aux)
            else:
                cs = 0

            bbb = math.tan(declina) / math.tan(lat_radians)
            if math.cos(solar_angle) < bbb:
                cs = -cs
            return (cs, cw, cz)

    def sunrise_sunset(self, datetime):
        """Sunrise and sunset solar hour

        Args:
            datetime (datetime): Local hour

        Returns:
            (number, number): (sunrise, sunset)
        """
        day = datetime.timetuple().tm_yday  # Día del año
        declina = 23.45 * math.sin(2 * math.pi * (284 + day) / 365)
        solar_angle_cos = -math.tan(math.radians(self.latitude)) * math.tan(
            math.radians(declina)
        )
        if solar_angle_cos <= -1:  # Sun allways out
            return (0.0, 24.0)
        elif solar_angle_cos >= 1:  # Allways night
            return (0.0, 0.0)
        else:
            solar_angle = math.acos(solar_angle_cos)
            if solar_angle < 0:
                solar_angle += math.pi
            return (
                (12 - (12 * solar_angle) / math.pi),
                (12 + (12 * solar_angle) / math.pi),
            )
