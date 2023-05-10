import numpy as np
import datetime as dt
import math
from opensimula.parameters import Parameter_string
from opensimula.Component import Component


class File_met(Component):
    def __init__(self):
        Component.__init__(self)
        self.parameter["type"].value = "File_met"
        self.parameter["name"].value = "File_met_x"
        self.add_parameter(Parameter_string("file_name", "name.met"))
        # Las variables leidas las guardamos en numpy arrays
        self.temperature = np.zeros(8760)
        self.sky_temperature = np.zeros(8760)
        self.sol_direct = np.zeros(8760)
        self.sol_diffuse = np.zeros(8760)
        self.abs_humidity = np.zeros(8760)
        self.rel_humidity = np.zeros(8760)
        self.wind_speed = np.zeros(8760)
        self.wind_direction = np.zeros(8760)
        self.sol_azimut = np.zeros(8760)
        self.sol_cenit = np.zeros(8760)

    def check(self):
        # Read the file
        try:
            f = open(self.parameter["file_name"].value, "r")
        except OSError:
            print(
                "Error in component: ",
                self.parameter["name"].value,
                ", type: ",
                self.parameter["type"].value,
            )
            print("   could not open/read file: ", self.parameter["file_name"].value)
            return 1
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
                self.abs_humidity[t] = float(valores[7])
                self.rel_humidity[t] = float(valores[8])
                self.wind_speed[t] = float(valores[9])
                self.wind_direction[t] = float(valores[10])
                self.sol_azimut[t] = float(valores[11])
                self.sol_cenit[t] = float(valores[12])
        return 0

    def get_instant_values(self, datetime):
        """Dictonary with all the meteo values for the datatime"""
        assert isinstance(datetime, dt.datetime)
        # calcular al índice
        # El primer valor es a las 00:30
        index = self._solar_hour_(datetime) - 0.5
        if index < 0:
            index = index + 8760
        elif index >= 8760:
            index = index - 8760
        i = math.floor(index)
        j = i + 1
        if j >= 8760:
            j = 0
        f = index - i
        temperature = self.temperature[i] * (1 - f) + self.temperature[j] * f
        sky_temperature = (
            self.sky_temperature[i] * (1 - f) + self.sky_temperature[j] * f
        )
        sol_direct = self.sol_direct[i] * (1 - f) + self.sol_direct[j] * f
        sol_diffuse = self.sol_diffuse[i] * (1 - f) + self.sol_diffuse[j] * f
        abs_humidity = self.abs_humidity[i] * (1 - f) + self.abs_humidity[j] * f
        rel_humidity = self.rel_humidity[i] * (1 - f) + self.rel_humidity[j] * f
        wind_speed = self.wind_speed[i] * (1 - f) + self.wind_speed[j] * f
        wind_direction = self.wind_direction[i] * (1 - f) + self.wind_direction[j] * f
        sol_azimut = self.sol_azimut[i] * (1 - f) + self.sol_azimut[j] * f
        sol_cenit = self.sol_cenit[i] * (1 - f) + self.sol_cenit[j] * f
        return {
            "temperature": temperature,
            "sky_temperature": sky_temperature,
            "sol_direct": sol_direct,
            "sol_diffuse": sol_diffuse,
            "abs_humidity": abs_humidity,
            "rel_humidity": rel_humidity,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "sol_azimut": sol_azimut,
            "sol_cenit": sol_cenit,
        }

    def _solar_hour_(self, datetime):  # Hora solar desde el principio del año
        day = datetime.timetuple().tm_yday  # Día del año
        hours = (day - 1) * 24
        hours += datetime.hour + datetime.minute / 60 + datetime.second / 3600

        daylight_saving = (
            hours
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
