import numpy as np
import datetime as dt
import math
import psychrolib as sicro
from OpenSimula.Parameters import Parameter_string, Parameter_options
from OpenSimula.Component import Component
from OpenSimula.Variable import Variable


class File_met(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "File_met"
        self.parameter("description").value = "Meteorological file"
        # Parameters
        self.add_parameter(Parameter_string("file_name", "name.met"))
        self.add_parameter(Parameter_options(
            "file_type", "MET", ["MET", "TMY3"]))

        # Variables
        self.add_variable(Variable("sol_hour", unit="h"))
        self.add_variable(Variable("temperature", unit="°C"))
        self.add_variable(Variable("sky_temperature", unit="°C"))
        self.add_variable(Variable("underground_temperature", unit="°C"))
        self.add_variable(Variable("rel_humidity", unit="%"))
        self.add_variable(Variable("abs_humidity", unit="g/kg"))
        self.add_variable(Variable("dew_point_temp", unit="°C"))
        self.add_variable(Variable("wet_bulb_temp", unit="°C"))
        self.add_variable(Variable("sol_direct", unit="W/m²"))
        self.add_variable(Variable("sol_diffuse", unit="W/m²"))
        self.add_variable(Variable("wind_speed", unit="m/s"))
        self.add_variable(Variable("wind_direction", unit="°"))
        self.add_variable(Variable("sol_azimuth", unit="°"))
        self.add_variable(Variable("sol_altitude", unit="°"))
        self.add_variable(Variable("pressure", unit="Pa"))
        self.add_variable(Variable("total_cloud_cover", unit="%"))
        self.add_variable(Variable("opaque_cloud_cover", unit="%"))

        # Las variables leidas las guardamos en numpy arrays
        self.temperature = np.zeros(8760)
        self.sky_temperature = np.zeros(8760)
        self.sol_direct = np.zeros(8760)
        self.sol_diffuse = np.zeros(8760)
        self.rel_humidity = np.zeros(8760)
        self.wind_speed = np.zeros(8760)
        self.wind_direction = np.zeros(8760)
        self.pressure = np.zeros(8760)
        self.total_cloud_cover = np.zeros(8760)
        self.opaque_cloud_cover = np.zeros(8760)

    def check(self):
        errors = super().check()
        # Read the file
        try:
            f = open(self.parameter("file_name").value, "r")
        except OSError as error:
            errors.append(
                f"Error in component: {self.parameter('name').value}, could not open/read file: {self.parameter('file_name').value}"
            )
            return errors
        with f:
            if self.parameter("file_type").value == "MET":
                self._read_met_file(f)
            elif self.parameter("file_type").value == "TMY3":
                self._read_tmy3_file(f)
        return errors

    def _read_met_file(self, f):
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
            self.rel_humidity[t] = float(valores[8])
            self.wind_speed[t] = float(valores[9])
            self.wind_direction[t] = float(valores[10])
            # Atmosfera estándar con T = 20ºC
            self.pressure[t] = 101325 * math.exp(-1.1654*self.altitude)

        self._T_average = np.average(self.temperature)

    def _read_tmy3_file(self, f):
        sicro.SetUnitSystem(sicro.SI)
        line = f.readline()
        valores = line.split(",")
        self.latitude = float(valores[4])
        self.longitude = float(valores[5])
        self.altitude = float(valores[6])
        self.reference_time_longitude = float(valores[3])*15
        f.readline()  # Header line
        for t in range(8760):
            line = f.readline()
            valores = line.split(",")
            self.temperature[t] = float(valores[31])
            self.sol_direct[t] = float(valores[4]) - float(valores[10])
            self.sol_diffuse[t] = float(valores[10])
            self.rel_humidity[t] = float(valores[37])
            self.wind_speed[t] = float(valores[46])
            self.wind_direction[t] = float(valores[43])
            self.pressure[t] = float(valores[40]) * 100  # milibar to Pa
            self.total_cloud_cover[t] = float(valores[25])*10  # tenth to %
            self.opaque_cloud_cover[t] = float(valores[28])*10  # tenth to %
            self.sky_temperature[t] = self._t_sky_calculation(
                self.temperature[t], self.rel_humidity[t], self.opaque_cloud_cover[t])

        self._T_average = np.average(self.temperature)

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)

    def pre_iteration(self, time_index, date):
        solar_hour = self._solar_hour_(date)
        azi, alt = self.solar_pos(date, solar_hour)
        self.variable("sol_hour").values[time_index] = solar_hour
        self.variable("sol_azimuth").values[time_index] = azi
        self.variable("sol_altitude").values[time_index] = alt
        self.variable(
            "underground_temperature").values[time_index] = self._T_average
        if self.parameter("file_type").value == "MET":
            i, j, f = self._get_solar_interpolation_tuple_(date, solar_hour)
        elif self.parameter("file_type").value == "TMY3":
            i, j, f = self._get_local_interpolation_tuple_(date)

        self._interpolate("temperature", self.temperature, time_index, i, j, f)
        self._interpolate("rel_humidity", self.rel_humidity,
                          time_index, i, j, f)
        self._interpolate("sol_direct", self.sol_direct, time_index, i, j, f)
        self._interpolate("sol_diffuse", self.sol_diffuse,
                          time_index, i, j, f)
        self._interpolate("wind_speed", self.wind_speed,
                          time_index, i, j, f)
        self._interpolate("wind_direction", self.wind_direction,
                          time_index, i, j, f)
        self._interpolate("sky_temperature", self.sky_temperature,
                          time_index, i, j, f)
        self._interpolate("pressure", self.pressure,
                          time_index, i, j, f)
        self._interpolate("total_cloud_cover", self.total_cloud_cover,
                          time_index, i, j, f)
        self._interpolate("opaque_cloud_cover", self.opaque_cloud_cover,
                          time_index, i, j, f)
        # Corregir la directa si el sol no ha salido, y con alturas solares pequeñas
        if (alt <= 1 and self.variable("sol_direct").values[time_index] > 0):
            self.variable(
                "sol_diffuse").values[time_index] += self.variable("sol_direct").values[time_index]
            self.variable("sol_direct").values[time_index] = 0
        # calculate the rest of the psychrometric variables with T, HR and p
        T = self.variable("temperature").values[time_index]
        HR = self.variable("rel_humidity").values[time_index]/100
        p = self.variable("pressure").values[time_index]
        self.variable("abs_humidity").values[time_index] = sicro.GetHumRatioFromRelHum(
            T, HR, p)*1000
        self.variable("dew_point_temp").values[time_index] = sicro.GetTDewPointFromRelHum(
            T, HR)
        self.variable("wet_bulb_temp").values[time_index] = sicro.GetTWetBulbFromRelHum(
            T, HR, p)

    def _interpolate(self, variable, array, time_i, i, j, f):
        self.variable(
            variable).values[time_i] = array[i] * (1 - f) + array[j] * f

    def _get_solar_interpolation_tuple_(self, datetime, solar_hour):
        day = datetime.timetuple().tm_yday  # Día del año
        # El primer valor es a las 00:30
        index = solar_hour + (day-1)*24
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

    def _get_local_interpolation_tuple_(self, date):
        # a las 0:30 del primer día
        initial_date = dt.datetime(date.year, 1, 1, 0, 30)
        seconds = (date-initial_date).total_seconds()
        index = seconds / 3600
        if index < 0:
            index = 0
        elif index >= 8760:
            index = index - 8760
        i = math.floor(index)
        j = i + 1
        if j >= 8760:
            j = j - 8760
        f = index - i
        return (i, j, f)

    def _solar_hour_(self, datetime):  # Hora solar
        day = datetime.timetuple().tm_yday  # Día del año
        hours = (
            datetime.hour + datetime.minute / 60 + datetime.second / 3600
        )  # hora local

        # daylight_saving = (
        #    hours
        #    + (day - 1) * 24
        #    - (datetime.timestamp() - dt.datetime(datetime.year, 1, 1).timestamp())
        #    / 3600
        # )
        daylight_saving = 0
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

    def _t_sky_calculation(self, temp, rel_hum, opaque_cover):
        """Caclulation of Sky Temperature using the Clark & Allen correlaton (1978) and the correlation of Walton (1983)

        Args:
            temp (_type_): _description_
            rel_hum (_type_): _description_
            opaque_cover (_type_): _description_
        """
        dp_temp = sicro.GetTDewPointFromRelHum(temp, rel_hum/100)
        epsilon_clear = 0.787 + 0.764 * \
            math.log((dp_temp+273.15)/273)  # Clark & Allen
        N = opaque_cover/10  # opaque cover sky in tenths
        epsilon = epsilon_clear*(1+0.0224*N-0.0035*N**2+0.00028*N**3)  # Walton
        SIGMA = 5.6697E-8
        ir = SIGMA * epsilon * (temp + 273.15)**4
        t_sky = (ir/SIGMA)**0.25 - 273.15
        return t_sky

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
            return sol_direct * math.cos(theta) / math.sin(math.radians(sol_altitude))
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
            if cos > 1E-5:
                return math.acos(cos)
            else:
                return None
        else:
            return None
