## Component List for reading files

### File_met

component used to read and manage weather files. Creating the necessary weather variables to be used by other components.

#### Parameters
- **file_type** [_option_, default = "MET", options = ["MET","TMY3"]]: Weather file type. "MET": MET format. [.MET format (CTE documentation)](https://www.codigotecnico.org/pdf/Documentos/HE/20170202-DOC-DB-HE-0-Climas%20de%20referencia.pdf), "TMY3" TMY3 format [TMY3 format description](https://www.nrel.gov/docs/fy08osti/43156.pdf), "TMY2" TMY2 format [TMY2 format description](https://www.nrel.gov/docs/legosti/old/7668.pdf)
- **file_name** [_string_, default = "name.met"]: Name of the weather file containing the data. 
- **tilted_diffuse_model** [_option_, default = "PEREZ", options = ["PEREZ","REINDL","HAY-DAVIES", "ISOTROPIC"]]: Model used for the calculation of diffuse solar radiation on inclined surfaces. The simplest model is the isotropic model (“ISOTROPIC”) which only takes into account uniform diffuse radiation. The Hay-Davies model (default value) includes the influence of the circumsolar component and the Reindl and Perez model also includes the effect of the horizon brightening component. [More information about diffuse models on tilted surface](https://pvpmc.sandia.gov/modeling-guide/1-weather-design-inputs/plane-of-array-poa-irradiance/calculating-poa-irradiance/poa-sky-diffuse/)


**Example:**
<pre><code class="python">
...

met = pro.new_component("File_met","met")
met.parameter("file_name").value = "examples/met_files/sevilla.met"
</code></pre>

To generate the variables in the simulation time step, the values are obtained by linear interpolation of the data available in the meteorological file. The variables associated with the solar position are calculated, not obtained from the values stored in the file.

#### Variables
- **temperature** [°C]: Dry bulb temperature.
- **sky_temperature** [°C]: Sky temperature, for radiant heat exchange (read from MET files, calculated in TMY3 files).
- **underground_temperature** [°C]: Ground temperature, to be used as the temperature imposed on the outer surface of the enclosures in contact with the ground (currently not read from the file, it is calculated as the annual average air temperature).
- **abs_humidity** [g/kg]: Air absolute humidity (calculated).
- **rel_humidity** [%]: Air relative humidity.
- **dew_point_temp** [°C]: Dew point air temperature (calculated).
- **wet_bulb_temp** [°C]: Wet bulb air temperature (calculated).
- **sol_hour** [h]: Solar hour of the day (calculated).
- **sol_direct** [W/m²]: Direct solar irradiance over horizontal surface.
- **sol_diffuse** [W/m²]: Diffuse solar irradiance over horizontal surface.
- **sol_azimuth** [°]: Solar azimuth (degrees from south: E-, W+) (calculated).
- **sol_altitude** [°]: Solar altitude (degrees) (calculated).
- **wind_speed** [m/s]: Wind speed.
- **wind_direction** [°]: Wind direction (degrees from north: E+, W-).
- **pressure** [Pa]: Ambient absolute pressure (read from TMY3 files, calculated using standard atmosphere for MET files).
- **total_cloud_cover** [%]:  Percentage of the sky covered by all the visible clouds (read from TMY3 files, 0 for MET files).
- **opaque_cloud_cover** [%]: Percentage of the sky covered, used for infrared radiation an sky temperature estimation (read from TMY3 files, 0 for MET files).


### File_data

Component to read temporary data files and use them as simulation variables.

#### Parameters
- **file_name** [_string_, default = "data.csv"]: Name of the file containing the data.
- **file_type** [_option_, default = "CSV", options = ["CSV","EXCEL"]]: Data file type. "CSV", file with the values separated by comma. It must contain a first row with the variable names and from the second row the values for each time step. "EXCEL": excel file with a single sheet and the same format as described for CSV files.
- **file_step** [_option_, default = "SIMULATION", options = ["SIMULATION","OWN"]]: Time step of the data file. The "SIMULATION" option assumes that each of the rows in the data file correspond to the time steps of the project simulation. The "OWN" option will be used when the time step of the data stored in the data file is different from the one used in the simulation. The parameters "initial_time" and "time_step" define the time step of the data in the file.
- **initial_time** [_string_, default = "01/01/2001 00:00:00"]: Initial time of the data file with format "DD/MM/YYYY hh:mm:ss". Only used for the "OWN" option of the "file_step" parameter.
- **time_step** [_int_, unit = "s", default = 3600, min = 1]: Time step in seconds for the data file. Only used for the "OWN" option of the "file_step" parameter.

If we use the "SIMULATION" option of the "file_step" parameter and the number of data in the file is less than the number of time steps during the simulation, to obtain the variables we will go back to the beginning of the data file each time the end of the file is reached.

the first simulation instant is the initial_time plus 1/2 of the time_step. For example, if initial_time = “01/01/2001 00:00:00” and time_step = 3600, then the first simulation instant is: “01/01/2001 00:30:00”, the second: “01/01/2001 01:30:00”, and so on. 

If we use the "OWN" option of the "file_step" parameter and the simulated time instant is before or after the time instants collected in the file, the first value will be taken if it is before and the last one if it is after. Otherwise a linear interpolation will be performed to obtain the values of each of the simulation steps.

**Example:**
<pre><code class="python">
...

datas = osm.new_component("File_dat","datas")
param = {
    "file_name": "examples/input_files/data_example.csv",
    "file_type": "CSV",
    "file_step": "SIMULATION",
}
datas.set_parameters(param)
</code></pre>


#### Variables
The component will generate a variable for each of the columns of the data file, 
using as name and unit for the variable the first row of the file. 
The unit must be written after the name in square brackets.

For example for the following CSV file:

<pre><code class="Shell">
n, temperature [ºC], humidity [kg/kg as]
 1, 15.1, 0.00792
 2, 14.6, 0.00788
 3, 14.1, 0.00783
 4, 13.5, 0.00772
 5, 13.0, 0.00766
...
</code></pre>

Three variables will be created with names: n, temperature and humidity. And with the units indicated in square brackets.
