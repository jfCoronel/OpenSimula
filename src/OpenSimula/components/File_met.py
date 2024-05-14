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
            sicro.SetUnitSystem(sicro.SI)
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
            self.pressure[t] = 101325 * math.exp(-1.1654e-4*self.altitude)

        self._T_average = np.average(self.temperature)

    def _read_tmy3_file(self, f):
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

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        # solar_hour = self._solar_hour_(date)
        # azi, alt = self.solar_pos(date, solar_hour)
        azi, alt, solar_hour = self.sunpos(
            date, self.latitude, self.longitude, self.reference_time_longitude/15)
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

    def solar_direct_rad(self, time_index, surf_azimuth, surf_altitude):
        """Solar Direct radiation over surface

        Args:
            time_index (int): Simulation time index
            surf_azimuth (float): Surface azimuth
            surf_altitude (_type_): Surface altitude

        Returns:
            float: Solar direct radiation over surface (W/m^2)
        """
        theta = self.solar_surface_angle(
            time_index, surf_azimuth, surf_altitude)
        sol_direct = self.variable("sol_direct").values[time_index]
        sol_altitude = self.variable("sol_altitude").values[time_index]
        if theta is not None:
            return sol_direct * math.cos(theta) / math.sin(math.radians(sol_altitude))
        else:
            return 0

    def solar_diffuse_rad(self, time_index, surf_azimuth, surf_altitude):
        """Solar Diffuse radiation over surface
        Isotropic diffuse Model

        Args:
            time_index (int): Simulation time index
            surf_azimuth (float): Surface azimuth
            surf_altitude (_type_): Surface altitude

        Returns:
            float: Solar diffuse radiation over surface (W/m^2)
        """
        sol_diffuse = self.variable("sol_diffuse").values[time_index]

        # Isotropic diffuse radiation (Liu-Jordan model)
        E_dif_iso = sol_diffuse * (1 + math.sin(math.radians(surf_altitude)))/2

        # Anisotropic model ...
        # theta = self.solar_surface_angle(time_index, surf_azimuth, surf_altitude)
        # sol_direct = self.variable("sol_direct").values[time_index]
        # sol_altitude = self.variable("sol_altitude").values[time_index]
        # F not clear days
        # if sol_direct+sol_diffuse > 0:
        #    F = 1 - (sol_diffuse/(sol_diffuse+sol_direct))**2
        # else:
        #    F = 0
        # Horizont correction
        # f_1 = 1
        # if sol_diffuse > 0:
        #    f_1 = 1 + F*(math.sin(math.pi/2 - math.radians(surf_altitude)))**3
        # Near sun correction
        # f_2 = 1
        # if theta != None and surf_altitude != 90:
        #    f_2 = 1 + F * (math.cos(theta))**2 * \
        #        (math.sin(math.pi/2-math.radians(sol_altitude))**3)

        return E_dif_iso

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

    def sunpos(self, date, latitude, longitude, timezone):
        # Extract the passed data
        year = date.year
        month = date.month
        day = date.day
        hour = date.hour
        minute = date.minute
        second = date.second
        # Math typing shortcuts
        rad, deg = math.radians, math.degrees
        sin, cos, tan = math.sin, math.cos, math.tan
        asin, atan2 = math.asin, math.atan2
        # Convert latitude and longitude to radians
        rlat = rad(latitude)
        rlon = rad(longitude)
        # Decimal hour of the day at Greenwich
        greenwichtime = hour - timezone + minute / 60 + second / 3600
        # Days from J2000, accurate from 1901 to 2099
        daynum = (
            367 * year
            - 7 * (year + (month + 9) // 12) // 4
            + 275 * month // 9
            + day
            - 730531.5
            + greenwichtime / 24
        )
        # Mean longitude of the sun
        mean_long = daynum * 0.01720279239 + 4.894967873
        # Mean anomaly of the Sun
        mean_anom = daynum * 0.01720197034 + 6.240040768
        # Ecliptic longitude of the sun
        eclip_long = (
            mean_long
            + 0.03342305518 * sin(mean_anom)
            + 0.0003490658504 * sin(2 * mean_anom)
        )
        # Obliquity of the ecliptic
        obliquity = 0.4090877234 - 0.000000006981317008 * daynum
        # Right ascension of the sun
        rasc = atan2(cos(obliquity) * sin(eclip_long), cos(eclip_long))
        # Declination of the sun
        decl = asin(sin(obliquity) * sin(eclip_long))
        # Local sidereal time
        sidereal = 4.894961213 + 6.300388099 * daynum + rlon
        # Hour angle of the sun
        hour_ang = sidereal - rasc
        # Local elevation of the sun
        elevation = asin(sin(decl) * sin(rlat) + cos(decl)
                         * cos(rlat) * cos(hour_ang))
        # Local azimuth of the sun
        azimuth = atan2(
            -cos(decl) * cos(rlat) * sin(hour_ang),
            sin(decl) - sin(rlat) * sin(elevation),
        )
        # Convert azimuth and elevation to degrees
        azimuth = math.pi-azimuth  # South: 0, East 90
        azimuth = self._into_range_(deg(azimuth), -180, 180)
        elevation = self._into_range_(deg(elevation), -180, 180)
        # Refraction correction (optional)
        targ = rad((elevation + (10.3 / (elevation + 5.11))))
        elevation += (1.02 / tan(targ)) / 60

        # Solar hour
        hour_ang = self._into_range_(deg(hour_ang), -180, 180)
        solar_hour = hour_ang/15 + 12
        # Return azimuth and elevation in degrees
        return (round(azimuth, 3), round(elevation, 3), round(solar_hour, 3))

    def _into_range_(self, x, range_min, range_max):
        shiftedx = x - range_min
        delta = range_max - range_min
        return (((shiftedx % delta) + delta) % delta) + range_min
