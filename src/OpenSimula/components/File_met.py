import numpy as np
import datetime as dt
import math
import re  # Regular Expressions
import pandas as pd
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
            "file_type", "MET", ["MET", "TMY3", "TMY2"]))
        self.add_parameter(Parameter_options(
            "tilted_diffuse_model", "PEREZ", ["REINDL", "HAY-DAVIES", "ISOTROPIC", "PEREZ"]))

        # Variables
        self.add_variable(
            Variable("sol_hour", "h", "Solar hour of the day (calculated)"))
        self.add_variable(
            Variable("temperature", "°C", "Dry bulb temperature"))
        self.add_variable(Variable("sky_temperature", "°C",
                          "Sky temperature, for radiant heat exchange (read from MET files, calculated in TMY files)."))
        self.add_variable(Variable("underground_temperature", "°C",
                          "Ground temperature, to be used as the temperature imposed on the outer surface of the enclosures in contact with the ground (currently not read from the file, it is calculated as the annual average air temperature)."))
        self.add_variable(
            Variable("rel_humidity", "%", "Air relative humidity."))
        self.add_variable(Variable("abs_humidity", "g/kg",
                          "Air absolute humidity (calculated)."))
        self.add_variable(Variable("dew_point_temp", "°C",
                          "Dew point air temperature (calculated)."))
        self.add_variable(Variable("wet_bulb_temp", "°C",
                          "Wet bulb air temperature (calculated)."))
        self.add_variable(Variable("sol_direct", "W/m²",
                          "Direct solar irradiance over horizontal surface."))
        self.add_variable(Variable("sol_diffuse", "W/m²",
                          "Diffuse solar irradiance over horizontal surface."))
        self.add_variable(Variable("wind_speed", "m/s", "Wind speed."))
        self.add_variable(Variable("wind_direction", "°",
                          "Wind direction (degrees from north: E+, W-)."))
        self.add_variable(Variable(
            "sol_azimuth", "°", "Solar azimuth (degrees from south: E-, W+) (calculated)."))
        self.add_variable(Variable("sol_altitude", "°",
                          "Solar altitude (degrees) (calculated)."))
        self.add_variable(Variable(
            "pressure", "Pa", " Ambient absolute pressure (read from TMY files, calculated using standard atmosphere for MET files)."))
        self.add_variable(Variable("total_cloud_cover", "%",
                          "Percentage of the sky covered by all the visible clouds (read from TMY files, 0 for MET files)."))
        self.add_variable(Variable("opaque_cloud_cover", "%",
                          "Percentage of the sky covered, used for infrared radiation an sky temperature estimation (read from TMY files, 0 for MET files)."))

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
        sicro.SetUnitSystem(sicro.SI)
        if self.parameter("file_type").value == "MET":
            errors = self._read_met_file(errors)
        elif self.parameter("file_type").value == "TMY3":
            errors = self._read_tmy3_file(errors)
        elif self.parameter("file_type").value == "TMY2":
            errors = self._read_tmy2_file(errors)
        return errors

    def _read_met_file(self, errors):
        # Read the file
        try:
            f = open(self.parameter("file_name").value, "r")
        except OSError as error:
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
                self.rel_humidity[t] = float(valores[8])
                self.wind_speed[t] = float(valores[9])
                self.wind_direction[t] = float(valores[10])
                # Atmosfera estándar con T = 20ºC
                self.pressure[t] = 101325 * math.exp(-1.1654e-4*self.altitude)

        self._T_average = np.average(self.temperature)
        return errors

    def _read_tmy3_file(self, errors):
        # Read the file
        try:
            data, metadata = read_tmy3(self.parameter("file_name").value)
            self.latitude = metadata["latitude"]
            self.longitude = metadata["longitude"]
            self.altitude = metadata["altitude"]
            self.reference_time_longitude = metadata["TZ"]*15

            self.temperature = data["Dry-bulb (C)"].to_numpy()
            self.sol_diffuse = data["DHI (W/m^2)"].to_numpy()
            self.sol_direct = data["GHI (W/m^2)"].to_numpy() - self.sol_diffuse
            self.rel_humidity = data["RHum (%)"].to_numpy()

            self.wind_speed = data["Wspd (m/s)"].to_numpy()
            self.wind_direction = data["Wdir (degrees)"].to_numpy()
            # milibar to Pa
            self.pressure = data["Pressure (mbar)"].to_numpy() * 100
            self.total_cloud_cover = data["TotCld (tenths)"].to_numpy(
            ) * 10  # tenth to %
            self.opaque_cloud_cover = data["OpqCld (tenths)"].to_numpy(
            ) * 10  # tenth to %
            self._t_sky_calculation()
            self._T_average = np.average(self.temperature)
            return errors
        except OSError as error:
            errors.append(
                f"Error in component: {self.parameter('name').value}, could not open/read file: {self.parameter('file_name').value}"
            )
            return errors

    def _read_tmy2_file(self, errors):
        # Read the file
        try:
            data, metadata = read_tmy2(self.parameter("file_name").value)
            self.latitude = metadata["latitude"]
            self.longitude = metadata["longitude"]
            self.altitude = metadata["altitude"]
            self.reference_time_longitude = metadata["TZ"]*15

            self.temperature = data["DryBulb"].to_numpy()/10
            self.sol_diffuse = data["DHI"].to_numpy()
            self.sol_direct = data["GHI"].to_numpy() - self.sol_diffuse
            self.rel_humidity = data["RHum"].to_numpy()

            self.wind_speed = data["Wspd"].to_numpy()/10
            self.wind_direction = data["Wdir"].to_numpy()
            # milibar to Pa
            self.pressure = data["Pressure"].to_numpy() * 100
            self.total_cloud_cover = data["TotCld"].to_numpy(
            ) * 10  # tenth to %
            self.opaque_cloud_cover = data["OpqCld"].to_numpy(
            ) * 10  # tenth to %
            self._t_sky_calculation()
            self._T_average = np.average(self.temperature)
            return errors
        except OSError as error:
            errors.append(
                f"Error in component: {self.parameter('name').value}, could not open/read file: {self.parameter('file_name').value}"
            )
            return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        # solar_hour = self._solar_hour_(date)
        # azi, alt = self.solar_pos(date, solar_hour)
        azi, alt, solar_hour = self.sunpos(date)

        self.variable("sol_hour").values[time_index] = solar_hour
        if alt < 3:
            self.variable("sol_azimuth").values[time_index] = float("nan")
            self.variable("sol_altitude").values[time_index] = float("nan")
        else:
            self.variable("sol_azimuth").values[time_index] = azi
            self.variable("sol_altitude").values[time_index] = alt
        self.variable(
            "underground_temperature").values[time_index] = self._T_average
        if self.parameter("file_type").value == "MET":
            i, j, f = self._get_solar_interpolation_tuple_(date, solar_hour)
        elif self.parameter("file_type").value == "TMY3":
            i, j, f = self._get_local_interpolation_tuple_(date)
        elif self.parameter("file_type").value == "TMY2":
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
        if (alt < 3 and self.variable("sol_direct").values[time_index] > 0):
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

    def _t_sky_calculation(self):
        """Caclulation of Sky Temperature using the Clark & Allen correlaton (1978) and the correlation of Walton (1983)
        """
        SIGMA = 5.6697E-8
        for i in range(len(self.temperature)):
            dp_temp = sicro.GetTDewPointFromRelHum(
                self.temperature[i], self.rel_humidity[i]/100)
            epsilon_clear = 0.787 + 0.764 * \
                math.log((dp_temp+273.15)/273)  # Clark & Allen
            N = self.opaque_cloud_cover[i]/10  # opaque cover sky in tenths
            epsilon = epsilon_clear * \
                (1+0.0224*N-0.0035*N**2+0.00028*N**3)  # Walton
            ir = SIGMA * epsilon * (self.temperature[i] + 273.15)**4
            self.sky_temperature[i] = (ir/SIGMA)**0.25 - 273.15

    def solar_direct_rad(self, time_index, surf_azimuth, surf_altitude):
        """Solar Direct radiation over surface

        Args:
            time_index (int): Simulation time index
            surf_azimuth (float): Surface azimuth
            surf_altitude (_type_): Surface altitude

        Returns:
            float: Solar direct radiation over surface (W/m^2)
        """
        sol_direct = self.variable("sol_direct").values[time_index]
        if sol_direct == 0:
            return 0
        theta = self.solar_surface_angle(
            time_index, surf_azimuth, surf_altitude)
        sol_altitude = self.variable("sol_altitude").values[time_index]
        if theta is not None:
            return sol_direct * math.cos(theta) / math.sin(math.radians(sol_altitude))
        else:
            return 0

    def solar_diffuse_rad(self, time_index, surf_azimuth, surf_altitude):
        """Solar Diffuse radiation over surface

        Args:
            time_index (int): Simulation time index
            surf_azimuth (float): Surface azimuth
            surf_altitude (_type_): Surface altitude

        Returns:
            float: Solar diffuse radiation over surface (W/m^2)
        """
        sol_diffuse = self.variable("sol_diffuse").values[time_index]
        if (sol_diffuse == 0):
            return 0
        model = self.parameter("tilted_diffuse_model").value
        beta = math.radians(surf_altitude)
        if (model == "ISOTROPIC"):
            # Isotropic diffuse radiation (Liu-Jordan model)
            E_dif = sol_diffuse * (1 + math.sin(beta))/2
        elif (model == "HAY-DAVIES"):
            theta = self.solar_surface_angle(
                time_index, surf_azimuth, surf_altitude)
            if theta is not None:
                sol_direct = self.variable("sol_direct").values[time_index]
                sol_altitude = math.radians(self.variable(
                    "sol_altitude").values[time_index])
                A = sol_direct/math.sin(sol_altitude)/1353
                R_b = math.cos(theta) / math.sin(sol_altitude)
                E_dif = sol_diffuse * A * R_b + sol_diffuse * \
                    (1-A) * (1 + math.sin(beta))/2
            else:
                E_dif = sol_diffuse * (1 + math.sin(beta))/2
        elif (model == "REINDL"):
            theta = self.solar_surface_angle(
                time_index, surf_azimuth, surf_altitude)
            sol_altitude = math.radians(self.variable(
                "sol_altitude").values[time_index])
            sol_direct = self.variable("sol_direct").values[time_index]
            zenit = math.pi/2 - beta
            f_horizon = 1 + \
                math.sqrt(sol_direct/(sol_direct+sol_diffuse)) * \
                (math.sin(zenit/2))**3
            if theta is not None:
                A = sol_direct/math.sin(sol_altitude)/1353
                R_b = math.cos(theta) / math.sin(sol_altitude)
                E_dif = sol_diffuse * A * R_b + sol_diffuse * \
                    (1-A) * (1 + math.sin(beta))/2 * f_horizon
            else:
                E_dif = sol_diffuse * (1 + math.sin(beta))/2 * f_horizon
        elif (model == "PEREZ"):
            theta = self.solar_surface_angle(
                time_index, surf_azimuth, surf_altitude)
            if theta is None:  # No direct sun
                E_dif = sol_diffuse * (1 + math.sin(beta))/2
            else:
                sol_altitude = math.radians(self.variable(
                    "sol_altitude").values[time_index])
                sol_direct = self.variable("sol_direct").values[time_index]
                zenit = math.pi/2 - beta
                sol_zenit = math.pi/2 - sol_altitude
                epsilon = ((sol_direct/math.sin(sol_altitude)+sol_diffuse) /
                           sol_diffuse + 1.041 * sol_zenit**3)/(1 + 1.041*sol_zenit**3)
                m = 1 / math.cos(sol_zenit)
                Delta = m*sol_diffuse/1353
                f = self._perez_coef(epsilon)
                F_2 = f[3]+f[4]*Delta+f[5]*sol_zenit
                a = math.cos(theta)
                b = max(0.087156, math.cos(sol_zenit))
                F_1 = max(0, f[0]+f[1]*Delta+f[2]*sol_zenit)
                E_dif = sol_diffuse * \
                    ((1-F_1)*(1+math.cos(zenit))/2 +
                     F_1 * a/b + F_2 * math.sin(zenit))
        return E_dif

    def _perez_coef(self, epsilon):
        if epsilon > 1 and epsilon <= 1.065:
            return [-0.0083117, 0.5877285, -0.0620636, -0.0596012, 0.0721249, -0.0220216]
        elif epsilon > 1.065 and epsilon <= 1.23:
            return [0.1299457, 0.6825954, -0.1513752, -0.0189325, 0.0659650, -0.0288748]
        elif epsilon > 1.23 and epsilon <= 1.5:
            return [0.3296958, 0.4868735, -0.2210958, 0.055414, -0.0639588, -0.0260542]
        elif epsilon > 1.5 and epsilon <= 1.95:
            return [0.5682053, 0.1874525, -0.295129, 0.1088631, -0.1519229, -0.0139754]
        elif epsilon > 1.95 and epsilon <= 2.8:
            return [0.873028, -0.3920403, -0.3616149, 0.2255647, -0.4620442, 0.0012448]
        elif epsilon > 2.8 and epsilon <= 4.5:
            return [1.1326077, -1.2367284, -0.4118494, 0.2877813, -0.8230357, 0.0558651]
        elif epsilon > 4.5 and epsilon <= 6.2:
            return [1.0601591, -1.5999137, -0.3589221, 0.2642124, -1.127234, 0.1310694]
        elif epsilon > 6.2:
            return [0.677747, -0.3272588, -0.2504286, 0.1561313, -1.3765031, 0.2506212]

    def solar_surface_angle(self, time_index, surf_azimuth, surf_altitude):
        """Relative angle between surface exterior normal and the sum

        Args:
            time_index (int): _description_
            surf_azimuth (float): _description_
            surf_altitude (float): _description_

        Returns:
            float: Angle in radians
        """
        azi_sur = math.radians(surf_azimuth)
        alt_sur = math.radians(surf_altitude)
        sol_direct = self.variable("sol_direct").values[time_index]
        azi_sol = math.radians(self.variable("sol_azimuth").values[time_index])
        alt_sol = math.radians(self.variable(
            "sol_altitude").values[time_index])
        if sol_direct > 0:
            cos = math.cos(azi_sol)*math.cos(alt_sol) * math.cos(azi_sur) * math.cos(alt_sur) + math.sin(azi_sol) * \
                math.cos(alt_sol) * math.sin(azi_sur) * \
                math.cos(alt_sur) + math.sin(alt_sol) * math.sin(alt_sur)
            if cos > .05:  # angle < 87.13, problems with angles near to 90º
                return math.acos(cos)
            else:
                return None
        else:
            return None

    def sunpos(self, date):
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
        rlat = rad(self.latitude)
        rlon = rad(self.longitude)
        # Decimal hour of the day at Greenwich
        timezone = self.reference_time_longitude/15
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

    def sun_cosines(self, date):
        azi, alt, solar_hour = self.sunpos(date)
        if alt < 0:
            return []
        else:
            azi_rd = math.radians(azi)
            alt_rd = math.radians(alt)
            return np.array([math.cos(alt_rd)*math.sin(azi_rd), -math.cos(alt_rd)*math.cos(azi_rd), math.sin(alt_rd)])

    def maximun_solar_angles(self):
        azimuth = []
        altitude = []
        if (self.longitude > 0):
            solstice = dt.datetime(2001, 6, 21)
        else:
            solstice = dt.datetime(2001, 6, 22)
        for i in range(0, 23):
            solstice = solstice.replace(hour=i, minute=30)
            az, alt, hour = self.sunpos(solstice)
            if alt < 0:
                alt = 0
                az = 0
            azimuth.append(az)
            altitude.append(alt)
        return (max(azimuth), max(altitude))

    def _into_range_(self, x, range_min, range_max):
        shiftedx = x - range_min
        delta = range_max - range_min
        return (((shiftedx % delta) + delta) % delta) + range_min


def read_tmy3(filename, encoding=None):
    """Read a TMY3 file into a pandas dataframe.

    Note that values contained in the metadata dictionary are unchanged
    from the TMY3 file (i.e. units are retained). In the case of any
    discrepancies between this documentation and the TMY3 User's Manual
    [1]_, the TMY3 User's Manual takes precedence.

    The TMY3 files were updated in Jan. 2015. This function requires the
    use of the updated files.

    Parameters
    ----------
    filename : str
        A relative file path or absolute file path.

    encoding : str, optional
        Encoding of the file. For files that contain non-UTF8 characters it may
        be necessary to specify an alternative encoding, e.g., for
        SolarAnywhere TMY3 files the encoding should be 'iso-8859-1'. Users
        may also consider using the 'utf-8-sig' encoding.

    Returns
    -------
    Tuple of the form (data, metadata).

    data : DataFrame
        A pandas dataframe with the columns described in the table
        below. For more detailed descriptions of each component, please
        consult the TMY3 User's Manual [1]_, especially tables 1-1
        through 1-6.

    metadata : dict
        The site metadata available in the file.

    Notes
    -----
    The returned structures have the following fields.

    ===============   ======  ===================
    key               format  description
    ===============   ======  ===================
    altitude          Float   site elevation
    latitude          Float   site latitudeitude
    longitude         Float   site longitudeitude
    Name              String  site name
    State             String  state
    TZ                Float   UTC offset
    USAF              Int     USAF identifier
    ===============   ======  ===================


    ========================       ======================================================================================================================================================
    field                          description
    ========================       ======================================================================================================================================================
    Index                          A pandas datetime index. NOTE, the index is timezone aware, and times are set to local standard time (daylight savings is not included)
    ghi_extra                      Extraterrestrial horizontal radiation recv'd during 60 minutes prior to timestamp, Wh/m^2
    dni_extra                      Extraterrestrial normal radiation recv'd during 60 minutes prior to timestamp, Wh/m^2
    ghi                            Direct and diffuse horizontal radiation recv'd during 60 minutes prior to timestamp, Wh/m^2
    GHI source                     See [1]_, Table 1-4
    GHI uncert (%)                 Uncertainty based on random and bias error estimates see [2]_
    dni                            Amount of direct normal radiation (modeled) recv'd during 60 mintues prior to timestamp, Wh/m^2
    DNI source                     See [1]_, Table 1-4
    DNI uncert (%)                 Uncertainty based on random and bias error estimates see [2]_
    dhi                            Amount of diffuse horizontal radiation recv'd during 60 minutes prior to timestamp, Wh/m^2
    DHI source                     See [1]_, Table 1-4
    DHI uncert (%)                 Uncertainty based on random and bias error estimates see [2]_
    GH illum (lx)                  Avg. total horizontal illuminance recv'd during the 60 minutes prior to timestamp, lx
    GH illum source                See [1]_, Table 1-4
    GH illum uncert (%)            Uncertainty based on random and bias error estimates see [2]_
    DN illum (lx)                  Avg. direct normal illuminance recv'd during the 60 minutes prior to timestamp, lx
    DN illum source                See [1]_, Table 1-4
    DN illum uncert (%)            Uncertainty based on random and bias error estimates see [2]_
    DH illum (lx)                  Avg. horizontal diffuse illuminance recv'd during the 60 minutes prior to timestamp, lx
    DH illum source                See [1]_, Table 1-4
    DH illum uncert (%)            Uncertainty based on random and bias error estimates see [2]_
    Zenith lum (cd/m^2)            Avg. luminance at the sky's zenith during the 60 minutes prior to timestamp, cd/m^2
    Zenith lum source              See [1]_, Table 1-4
    Zenith lum uncert (%)          Uncertainty based on random and bias error estimates see [1]_ section 2.10
    TotCld (tenths)                Amount of sky dome covered by clouds or obscuring phenonema at time stamp, tenths of sky
    TotCld source                  See [1]_, Table 1-5
    TotCld uncert (code)           See [1]_, Table 1-6
    OpqCld (tenths)                Amount of sky dome covered by clouds or obscuring phenonema that prevent observing the sky at time stamp, tenths of sky
    OpqCld source                  See [1]_, Table 1-5
    OpqCld uncert (code)           See [1]_, Table 1-6
    temp_air                       Dry bulb temperature at the time indicated, deg C
    Dry-bulb source                See [1]_, Table 1-5
    Dry-bulb uncert (code)         See [1]_, Table 1-6
    temp_dew                       Dew-point temperature at the time indicated, deg C
    Dew-point source               See [1]_, Table 1-5
    Dew-point uncert (code)        See [1]_, Table 1-6
    relative_humidity              Relatitudeive humidity at the time indicated, percent
    RHum source                    See [1]_, Table 1-5
    RHum uncert (code)             See [1]_, Table 1-6
    pressure                       Station pressure at the time indicated, 1 mbar
    Pressure source                See [1]_, Table 1-5
    Pressure uncert (code)         See [1]_, Table 1-6
    wind_direction                 Wind direction at time indicated, degrees from north (360 = north; 0 = undefined,calm)
    Wdir source                    See [1]_, Table 1-5
    Wdir uncert (code)             See [1]_, Table 1-6
    wind_speed†                    Wind speed at the time indicated, meter/second
    Wspd source                    See [1]_, Table 1-5
    Wspd uncert (code)             See [1]_, Table 1-6
    Hvis (m)                       Distance to discernable remote objects at time indicated (7777=unlimited), meter
    Hvis source                    See [1]_, Table 1-5
    Hvis uncert (coe)              See [1]_, Table 1-6
    CeilHgt (m)                    Height of cloud base above local terrain (7777=unlimited), meter
    CeilHgt source                 See [1]_, Table 1-5
    CeilHgt uncert (code)          See [1]_, Table 1-6
    precipitable_water             Total precipitable water contained in a column of unit cross section from earth to top of atmosphere, cm
    Pwat source                    See [1]_, Table 1-5
    Pwat uncert (code)             See [1]_, Table 1-6
    AOD                            The broadband aerosol optical depth per unit of air mass due to extinction by aerosol component of atmosphere, unitless
    AOD source                     See [1]_, Table 1-5
    AOD uncert (code)              See [1]_, Table 1-6
    albedo†                        The ratio of reflected solar irradiance to global horizontal irradiance, unitless
    Alb source                     See [1]_, Table 1-5
    Alb uncert (code)              See [1]_, Table 1-6
    Lprecip depth (mm)             The amount of liquid precipitation observed at indicated time for the period indicated in the liquid precipitation quantity field, millimeter
    Lprecip quantity (hr)          The period of accumulatitudeion for the liquid precipitation depth field, hour
    Lprecip source                 See [1]_, Table 1-5
    Lprecip uncert (code)          See [1]_, Table 1-6
    PresWth (METAR code)           Present weather code, see [2]_.
    PresWth source                 Present weather code source, see [2]_.
    PresWth uncert (code)          Present weather code uncertainty, see [2]_.
    ========================       ======================================================================================================================================================

    .. admonition:: Midnight representation

       The function is able to handle midnight represented as 24:00 (NREL TMY3
       format, see [1]_) and as 00:00 (SolarAnywhere TMY3 format, see [3]_).

    .. warning:: TMY3 irradiance data corresponds to the *previous* hour, so
        the first index is 1AM, corresponding to the irradiance from midnight
        to 1AM, and the last index is midnight of the *next* year. For example,
        if the last index in the TMY3 file was 1988-12-31 24:00:00 this becomes
        1989-01-01 00:00:00.

    References
    ----------
    .. [1] Wilcox, S and Marion, W. "Users Manual for TMY3 Data Sets".
       NREL/TP-581-43156, Revised May 2008.
       :doi:`10.2172/928611`
    .. [2] Wilcox, S. (2007). National Solar Radiation Database 1991 2005
       Update: Users Manual. 472 pp.; NREL Report No. TP-581-41364.
       :doi:`10.2172/901864`
    .. [3] `SolarAnywhere file formats
       <https://www.solaranywhere.com/support/historical-data/file-formats/>`_
    """  # noqa: E501
    head = ['USAF', 'Name', 'State', 'TZ', 'latitude', 'longitude', 'altitude']

    with open(str(filename), 'r', encoding=encoding) as fbuf:
        # header information on the 1st line (0 indexing)
        firstline = fbuf.readline()
        # use pandas to read the csv file buffer
        # header is actually the second line, but tell pandas to look for
        data = pd.read_csv(fbuf, header=0)

    meta = dict(zip(head, firstline.rstrip('\n').split(",")))
    # convert metadata strings to numeric types
    meta['altitude'] = float(meta['altitude'])
    meta['latitude'] = float(meta['latitude'])
    meta['longitude'] = float(meta['longitude'])
    meta['TZ'] = float(meta['TZ'])
    meta['USAF'] = int(meta['USAF'])

    # get the date column as a pd.Series of numpy datetime64
    data_ymd = pd.to_datetime(data['Date (MM/DD/YYYY)'], format='%m/%d/%Y')
    # extract minutes
    minutes = data['Time (HH:MM)'].str.split(':').str[1].astype(int)
    # shift the time column so that midnite is 00:00 instead of 24:00
    shifted_hour = data['Time (HH:MM)'].str.split(':').str[0].astype(int) % 24
    # shift the dates at midnight (24:00) so they correspond to the next day.
    # If midnight is specified as 00:00 do not shift date.
    data_ymd[data['Time (HH:MM)'].str[:2] == '24'] += dt.timedelta(days=1)  # noqa: E501
    # NOTE: as of pandas>=0.24 the pd.Series.array has a month attribute, but
    # in pandas-0.18.1, only DatetimeIndex has month, but indices are immutable
    # so we need to continue to work with the panda series of dates `data_ymd`
    data_index = pd.DatetimeIndex(data_ymd)
    # use indices to check for a leap day and advance it to March 1st
    leapday = (data_index.month == 2) & (data_index.day == 29)
    data_ymd[leapday] += dt.timedelta(days=1)

    # NOTE: as of pvlib-0.6.3, min req is pandas-0.18.1, so pd.to_timedelta
    # unit must be in (D,h,m,s,ms,us,ns), but pandas>=0.24 allows unit='hour'
    data.index = data_ymd + pd.to_timedelta(shifted_hour, unit='h') \
        + pd.to_timedelta(minutes, unit='min')

    data = data.tz_localize(int(meta['TZ'] * 3600))

    return data, meta


def read_tmy2(filename):
    """
    Read a TMY2 file into a DataFrame.

    Note that values contained in the DataFrame are unchanged from the
    TMY2 file (i.e. units  are retained). Time/Date and location data
    imported from the TMY2 file have been modified to a "friendlier"
    form conforming to modern conventions (e.g. N latitude is postive, E
    longitude is positive, the "24th" hour of any day is technically the
    "0th" hour of the next day). In the case of any discrepencies
    between this documentation and the TMY2 User's Manual [1]_, the TMY2
    User's Manual takes precedence.

    Parameters
    ----------
    filename : str
        A relative or absolute file path.

    Returns
    -------
    Tuple of the form (data, metadata).

    data : DataFrame
        A dataframe with the columns described in the table below. For a
        more detailed descriptions of each component, please consult the
        TMY2 User's Manual [1]_, especially tables 3-1 through 3-6, and
        Appendix B.

    metadata : dict
        The site metadata available in the file.

    Notes
    -----
    The returned structures have the following fields.

    =============    ==================================
    key              description
    =============    ==================================
    WBAN             Site identifier code (WBAN number)
    City             Station name
    State            Station state 2 letter designator
    TZ               Hours from Greenwich
    latitude         Latitude in decimal degrees
    longitude        Longitude in decimal degrees
    altitude         Site elevation in meters
    =============    ==================================

    ============================   ==========================================================================================================================================================================
    field                           description
    ============================   ==========================================================================================================================================================================
    index                           Pandas timeseries object containing timestamps
    year
    month
    day
    hour
    ETR                             Extraterrestrial horizontal radiation recv'd during 60 minutes prior to timestamp, Wh/m^2
    ETRN                            Extraterrestrial normal radiation recv'd during 60 minutes prior to timestamp, Wh/m^2
    GHI                             Direct and diffuse horizontal radiation recv'd during 60 minutes prior to timestamp, Wh/m^2
    GHISource                       See [1]_, Table 3-3
    GHIUncertainty                  See [1]_, Table 3-4
    DNI                             Amount of direct normal radiation (modeled) recv'd during 60 mintues prior to timestamp, Wh/m^2
    DNISource                       See [1]_, Table 3-3
    DNIUncertainty                  See [1]_, Table 3-4
    DHI                             Amount of diffuse horizontal radiation recv'd during 60 minutes prior to timestamp, Wh/m^2
    DHISource                       See [1]_, Table 3-3
    DHIUncertainty                  See [1]_, Table 3-4
    GHillum                         Avg. total horizontal illuminance recv'd during the 60 minutes prior to timestamp, units of 100 lux (e.g. value of 50 = 5000 lux)
    GHillumSource                   See [1]_, Table 3-3
    GHillumUncertainty              See [1]_, Table 3-4
    DNillum                         Avg. direct normal illuminance recv'd during the 60 minutes prior to timestamp, units of 100 lux
    DNillumSource                   See [1]_, Table 3-3
    DNillumUncertainty              See [1]_, Table 3-4
    DHillum                         Avg. horizontal diffuse illuminance recv'd during the 60 minutes prior to timestamp, units of 100 lux
    DHillumSource                   See [1]_, Table 3-3
    DHillumUncertainty              See [1]_, Table 3-4
    Zenithlum                       Avg. luminance at the sky's zenith during the 60 minutes prior to timestamp, units of 10 Cd/m^2 (e.g. value of 700 = 7,000 Cd/m^2)
    ZenithlumSource                 See [1]_, Table 3-3
    ZenithlumUncertainty            See [1]_, Table 3-4
    TotCld                          Amount of sky dome covered by clouds or obscuring phenonema at time stamp, tenths of sky
    TotCldSource                    See [1]_, Table 3-5
    TotCldUncertainty                See [1]_, Table 3-6
    OpqCld                          Amount of sky dome covered by clouds or obscuring phenonema that prevent observing the sky at time stamp, tenths of sky
    OpqCldSource                    See [1]_, Table 3-5
    OpqCldUncertainty               See [1]_, Table 3-6
    DryBulb                         Dry bulb temperature at the time indicated, in tenths of degree C (e.g. 352 = 35.2 C).
    DryBulbSource                   See [1]_, Table 3-5
    DryBulbUncertainty              See [1]_, Table 3-6
    DewPoint                        Dew-point temperature at the time indicated, in tenths of degree C (e.g. 76 = 7.6 C).
    DewPointSource                  See [1]_, Table 3-5
    DewPointUncertainty             See [1]_, Table 3-6
    RHum                            Relative humidity at the time indicated, percent
    RHumSource                      See [1]_, Table 3-5
    RHumUncertainty                 See [1]_, Table 3-6
    Pressure                        Station pressure at the time indicated, 1 mbar
    PressureSource                  See [1]_, Table 3-5
    PressureUncertainty             See [1]_, Table 3-6
    Wdir                            Wind direction at time indicated, degrees from east of north (360 = 0 = north; 90 = East; 0 = undefined,calm)
    WdirSource                      See [1]_, Table 3-5
    WdirUncertainty                 See [1]_, Table 3-6
    Wspd                            Wind speed at the time indicated, in tenths of meters/second (e.g. 212 = 21.2 m/s)
    WspdSource                      See [1]_, Table 3-5
    WspdUncertainty                 See [1]_, Table 3-6
    Hvis                            Distance to discernable remote objects at time indicated (7777=unlimited, 9999=missing data), in tenths of kilometers (e.g. 341 = 34.1 km).
    HvisSource                      See [1]_, Table 3-5
    HvisUncertainty                 See [1]_, Table 3-6
    CeilHgt                         Height of cloud base above local terrain (7777=unlimited, 88888=cirroform, 99999=missing data), in meters
    CeilHgtSource                   See [1]_, Table 3-5
    CeilHgtUncertainty              See [1]_, Table 3-6
    Pwat                            Total precipitable water contained in a column of unit cross section from Earth to top of atmosphere, in millimeters
    PwatSource                      See [1]_, Table 3-5
    PwatUncertainty                 See [1]_, Table 3-6
    AOD                             The broadband aerosol optical depth (broadband turbidity) in thousandths on the day indicated (e.g. 114 = 0.114)
    AODSource                       See [1]_, Table 3-5
    AODUncertainty                  See [1]_, Table 3-6
    SnowDepth                       Snow depth in centimeters on the day indicated, (999 = missing data).
    SnowDepthSource                 See [1]_, Table 3-5
    SnowDepthUncertainty            See [1]_, Table 3-6
    LastSnowfall                    Number of days since last snowfall (maximum value of 88, where 88 = 88 or greater days; 99 = missing data)
    LastSnowfallSource              See [1]_, Table 3-5
    LastSnowfallUncertainty         See [1]_, Table 3-6
    PresentWeather                  See [1]_, Appendix B. Each string contains 10 numeric values. The string can be parsed to determine each of 10 observed weather metrics.
    ============================   ==========================================================================================================================================================================

    References
    ----------
    .. [1] Marion, W and Urban, K. "Wilcox, S and Marion, W. "User's Manual
       for TMY2s". NREL 1995.
       :doi:`10.2172/87130`
    """  # noqa: E501
    # paste in the column info as one long line
    string = '%2d%2d%2d%2d%4d%4d%4d%1s%1d%4d%1s%1d%4d%1s%1d%4d%1s%1d%4d%1s%1d%4d%1s%1d%4d%1s%1d%2d%1s%1d%2d%1s%1d%4d%1s%1d%4d%1s%1d%3d%1s%1d%4d%1s%1d%3d%1s%1d%3d%1s%1d%4d%1s%1d%5d%1s%1d%10d%3d%1s%1d%3d%1s%1d%3d%1s%1d%2d%1s%1d'  # noqa: E501
    columns = 'year,month,day,hour,ETR,ETRN,GHI,GHISource,GHIUncertainty,DNI,DNISource,DNIUncertainty,DHI,DHISource,DHIUncertainty,GHillum,GHillumSource,GHillumUncertainty,DNillum,DNillumSource,DNillumUncertainty,DHillum,DHillumSource,DHillumUncertainty,Zenithlum,ZenithlumSource,ZenithlumUncertainty,TotCld,TotCldSource,TotCldUncertainty,OpqCld,OpqCldSource,OpqCldUncertainty,DryBulb,DryBulbSource,DryBulbUncertainty,DewPoint,DewPointSource,DewPointUncertainty,RHum,RHumSource,RHumUncertainty,Pressure,PressureSource,PressureUncertainty,Wdir,WdirSource,WdirUncertainty,Wspd,WspdSource,WspdUncertainty,Hvis,HvisSource,HvisUncertainty,CeilHgt,CeilHgtSource,CeilHgtUncertainty,PresentWeather,Pwat,PwatSource,PwatUncertainty,AOD,AODSource,AODUncertainty,SnowDepth,SnowDepthSource,SnowDepthUncertainty,LastSnowfall,LastSnowfallSource,LastSnowfallUncertaint'  # noqa: E501
    hdr_columns = 'WBAN,City,State,TZ,latitude,longitude,altitude'

    tmy2, tmy2_meta = _read_tmy2(string, columns, hdr_columns, str(filename))

    return tmy2, tmy2_meta


def _parsemeta_tmy2(columns, line):
    """Retrieve metadata from the top line of the tmy2 file.

    Parameters
    ----------
    columns : string
        String of column headings in the header

    line : string
        Header string containing DataFrame

    Returns
    -------
    meta : Dict of metadata contained in the header string
    """
    # Remove duplicated spaces, and read in each element
    rawmeta = " ".join(line.split()).split(" ")
    meta = rawmeta[:3]  # take the first string entries
    meta.append(int(rawmeta[3]))
    # Convert to decimal notation with S negative
    longitude = (
        float(rawmeta[5]) + float(rawmeta[6])/60) * (2*(rawmeta[4] == 'N') - 1)
    # Convert to decimal notation with W negative
    latitude = (
        float(rawmeta[8]) + float(rawmeta[9])/60) * (2*(rawmeta[7] == 'E') - 1)
    meta.append(longitude)
    meta.append(latitude)
    meta.append(float(rawmeta[10]))

    # Creates a dictionary of metadata
    meta_dict = dict(zip(columns.split(','), meta))
    return meta_dict


def _read_tmy2(string, columns, hdr_columns, fname):
    head = 1
    date = []
    with open(fname) as infile:
        fline = 0
        for line in infile:
            # Skip the header
            if head != 0:
                meta = _parsemeta_tmy2(hdr_columns, line)
                head -= 1
                continue
            # Reset the cursor and array for each line
            cursor = 1
            part = []
            for marker in string.split('%'):
                # Skip the first line of markers
                if marker == '':
                    continue

                # Read the next increment from the marker list
                increment = int(re.findall(r'\d+', marker)[0])
                next_cursor = cursor + increment

                # Extract the value from the line in the file
                val = (line[cursor:next_cursor])
                # increment the cursor by the length of the read value
                cursor = next_cursor

                # Determine the datatype from the marker string
                if marker[-1] == 'd':
                    try:
                        val = float(val)
                    except ValueError:
                        raise ValueError('WARNING: In {} Read value is not an '
                                         'integer " {} " '.format(fname, val))
                elif marker[-1] == 's':
                    try:
                        val = str(val)
                    except ValueError:
                        raise ValueError('WARNING: In {} Read value is not a '
                                         'string " {} " '.format(fname, val))
                else:
                    raise Exception('WARNING: In {} Improper column DataFrame '
                                    '" %{} " '.format(__name__, marker))

                part.append(val)

            if fline == 0:
                axes = [part]
                year = part[0] + 1900
                fline = 1
            else:
                axes.append(part)

            # Create datetime objects from read data
            date.append(dt.datetime(year=int(year),
                                    month=int(part[1]),
                                    day=int(part[2]),
                                    hour=(int(part[3]) - 1)))

    data = pd.DataFrame(
        axes, index=date,
        columns=columns.split(',')).tz_localize(int(meta['TZ'] * 3600))

    return data, meta
