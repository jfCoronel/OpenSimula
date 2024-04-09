import numpy as np
import datetime as dt
import math
from OpenSimula.Parameters import Parameter_string
from OpenSimula.Component import Component
from OpenSimula.Variable import Variable


class File_met(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "File_met"
        self.parameter("description").value = "Meteo file in met format"
        # Parameters
        self.add_parameter(Parameter_string("file_name", "name.met"))
        # Variables
        self.add_variable(Variable("sol_hour", unit="h"))
        self.add_variable(Variable("temperature", unit="°C"))
        self.add_variable(Variable("sky_temperature", unit="°C"))
        self.add_variable(Variable("underground_temperature", unit="°C"))
        self.add_variable(Variable("rel_humidity", unit="%"))
        self.add_variable(Variable("abs_humidity", unit="g/kg"))
        self.add_variable(Variable("sol_direct", unit="W/m²"))
        self.add_variable(Variable("sol_diffuse", unit="W/m²"))
        self.add_variable(Variable("wind_speed", unit="m/s"))
        self.add_variable(Variable("wind_direction", unit="°"))
        self.add_variable(Variable("sol_azimuth", unit="°"))
        self.add_variable(Variable("sol_altitude", unit="°"))
        # Las variables leidas las guardamos en numpy arrays
        self.temperature = np.zeros(8760)
        self.sky_temperature = np.zeros(8760)
        self.sol_direct = np.zeros(8760)
        self.sol_diffuse = np.zeros(8760)
        self.abs_humidity = np.zeros(8760)
        self.rel_humidity = np.zeros(8760)
        self.wind_speed = np.zeros(8760)
        self.wind_direction = np.zeros(8760)
        self.sol_azimuth = np.zeros(8760)
        self.sol_cenit = np.zeros(8760)

    def check(self):
        errors = super().check()
        # Read the file
        try:
            f = open(self.parameter("file_name").value, "r")
        except OSError:
            errors.append(
                f"Error in component: {self.parameter('name').value}, could not open/read file: {self.parameter('file_name').value}"
            )
            return errors
        with f:
            f.readline()
            line = f.readline()
            valores = line.split()
            self.latitude = float(valores[0])
            self.longitude = float(valores[1])
            self.altitude = float(valores[2])
            self.reference_time_longitude = float(valores[3])
            for t in range(8760):
                line = f.readline()
                valores = line.split()
                self.temperature[t] = float(valores[3])
                self.sky_temperature[t] = float(valores[4])
                self.sol_direct[t] = float(valores[5])
                self.sol_diffuse[t] = float(valores[6])
                self.abs_humidity[t] = float(valores[7])*1000
                self.rel_humidity[t] = float(valores[8])
                self.wind_speed[t] = float(valores[9])
                self.wind_direction[t] = float(valores[10])
                self.sol_azimuth[t] = float(valores[11])
                self.sol_cenit[t] = float(valores[12])
            self._T_average = np.average(self.temperature)
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)

    def pre_iteration(self, time_index, date):
        solar_hour = self._solar_hour_(date)
        self.variable("sol_hour").values[time_index] = solar_hour
        i, j, f = self._get_interpolation_tuple_(date, solar_hour)
        self.variable(
            "temperature").values[time_index] = self.temperature[i] * (1 - f) + self.temperature[j] * f
        self.variable("sky_temperature").values[time_index] = self.sky_temperature[i] * (
            1 - f) + self.sky_temperature[j] * f
        self.variable("rel_humidity").values[time_index] = self.rel_humidity[i] * (
            1 - f) + self.rel_humidity[j] * f
        self.variable("abs_humidity").values[time_index] = self.abs_humidity[i] * (
            1 - f) + self.abs_humidity[j] * f
        self.variable(
            "sol_direct").values[time_index] = self.sol_direct[i] * (1 - f) + self.sol_direct[j] * f
        self.variable(
            "sol_diffuse").values[time_index] = self.sol_diffuse[i] * (1 - f) + self.sol_diffuse[j] * f
        self.variable(
            "wind_speed").values[time_index] = self.wind_speed[i] * (1 - f) + self.wind_speed[j] * f
        self.variable("wind_direction").values[time_index] = self.wind_direction[i] * (
            1 - f) + self.wind_direction[j] * f
        azi, alt = self.solar_pos(date, solar_hour)
        self.variable("sol_azimuth").values[time_index] = azi
        self.variable("sol_altitude").values[time_index] = alt
        self.variable(
            "underground_temperature").values[time_index] = self._T_average

    def _get_interpolation_tuple_(self, datetime, solar_hour):
        day = datetime.timetuple().tm_yday  # Día del año
        # El primer valor es a las 00:30
        index = solar_hour + (day-1)*24 - 0.5
        if index < 0:
            index = index + 8760
        elif index >= 8760:
            index = index - 8760
        i = math.floor(index)
        j = i + 1
        if j >= 8760:
            j = 0
        f = index - i
        return (i, j, f)

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
        longitude_correction = (
            self.reference_time_longitude - self.longitude) * 1 / 15
        hours += ecuacion_tiempo / 60 - daylight_saving - longitude_correction
        return hours

    def solar_pos(self, datetime, solar_hour):
        """Solar position

        Args:
            datetime (datetime): local time

        Returns:
            (number, number): (solar azimuth, solar altitude)
        """
        sunrise, sunset = self.sunrise_sunset(datetime)
        if solar_hour < sunrise or solar_hour > sunset:
            return (0.0, 0.0)
        else:
            cs, cw, cz = self._solar_pos_cos_(datetime, solar_hour)
            alt = math.atan(cz / math.sqrt(1.0 - cz**2))
            aux = cw / math.cos(alt)
            azi = 0.0
            if aux == -1.0:  # justo Este
                azi = math.pi / 2
            elif aux == 1.0:  # justo Oeste
                azi = -math.pi / 2
            else:
                azi = -math.atan(aux / math.sqrt(1 - aux**2))
                if azi < 0:
                    if cs < 0:
                        azi = -math.pi - azi
                else:
                    if cs < 0:
                        azi = math.pi - azi
            return (azi * 180 / math.pi, alt * 180 / math.pi)

    def _solar_pos_cos_(self, datetime, solar_hour):
        """Solar position cosines

        Args:
            datetime (datetime): local time

        Returns:
            (number, number, number): (cos south, cost west, cos z)
        """

        day = datetime.timetuple().tm_yday  # Día del año
        declina = math.radians(
            23.45 * math.sin(2 * math.pi * (284 + day) / 365))
        solar_angle = math.radians(15 * (solar_hour - 12))
        lat_radians = math.radians(self.latitude)

        cz = math.sin(lat_radians) * math.sin(declina) + \
            math.cos(lat_radians) * math.cos(declina) * math.cos(solar_angle)
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

    def solar_direct_rad(self, time_index, surf_azimuth, surf_altitude):
        theta = self.solar_surface_angle(
            time_index, surf_azimuth, surf_altitude)
        sol_direct = self.variable("sol_direct").values[time_index]
        sol_altitude = self.variable("sol_altitude").values[time_index]
        if theta is not None:
            return sol_direct * math.cos(theta) / math.cos(math.radians(sol_altitude))
        else:
            return 0

    def solar_surface_angle(self, time_index, surf_azimuth, surf_altitude):
        """Relative angle between surface exterior normal and the sum

        Args:
            time_index (int): _description_
            surf_azimuth (float): _description_
            surf_altitude (float): _description_

        Returns:
            float: Angle in radians
        """
        sol_direct = self.variable("sol_direct").values[time_index]
        sol_azimuth = self.variable("sol_azimuth").values[time_index]
        sol_altitude = self.variable("sol_altitude").values[time_index]
        if sol_direct > 0:
            cos = math.cos(math.radians(sol_azimuth))*math.cos(math.radians(sol_altitude)) * \
                math.cos(math.radians(surf_azimuth)) * math.cos(math.radians(surf_altitude)) + \
                math.sin(math.radians(sol_azimuth))*math.cos(math.radians(sol_altitude)) * \
                math.sin(math.radians(surf_azimuth)) * math.cos(math.radians(surf_altitude)) + \
                math.sin(math.radians(sol_altitude)) * \
                math.sin(math.radians(surf_altitude))
            if cos > 1E-10:
                return math.acos(cos)
            else:
                return None
        else:
            return None
