import numpy as np
from opensimula.parameters import Parameter_string
from opensimula.Component import Component


class File_met(Component):
    def __init__(self):
        Component.__init__(self)
        self.parameter["type"].value = "File_met"
        self.add_parameter(Parameter_string("file_name", "name.met"))
        # Las variables leidas las guardamos en numpy arrays
        self.temperature = np.zeros(8760)
        self.sky_temperature = np.zeros(8760)
        self.sol_dir = np.zeros(8760)
        self.sol_dif = np.zeros(8760)
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
            self.message("Error: Could not open/read file: " +
                         self.parameter["file_name"].value)
            return False
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
                self.sol_dir[t] = float(valores[5])
                self.sol_dif[t] = float(valores[6])
                self.abs_humidity[t] = float(valores[7])
                self.rel_humidity[t] = float(valores[8])
                self.wind_speed[t] = float(valores[9])
                self.wind_direction[t] = float(valores[10])
                self.sol_azimut[t] = float(valores[11])
                self.sol_cenit[t] = float(valores[12])
