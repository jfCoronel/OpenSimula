from OpenSimula.Parameters import Parameter_component, Parameter_float
from OpenSimula.Component import Component
from OpenSimula.Variable import Variable
import psychrolib as sicro


class HVAC_DX_system(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_DX_system"
        self.parameter("description").value = "HVAC Direct Expansion system for time simulation"
        self.add_parameter(Parameter_component("equipment", "not_defined", ["HVAC_DX_equipment"]))
        self.add_parameter(Parameter_component("space", "not_defined", ["Space"])) # Space, TODO: Add Air_distribution, Energy_load
        self.add_parameter(Parameter_component("file_met", "not_defined", ["File_met"]))
        self.add_parameter(Parameter_float("supply_air_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("outdoor_air_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("cooling_bandwidth", 1, "ºC", min=0))
        self.add_parameter(Parameter_float("heating_bandwidth", 1, "ºC", min=0))

        # Variables
        self.add_variable(Variable("T_odb", unit="°C"))
        self.add_variable(Variable("T_owb", unit="°C"))
        self.add_variable(Variable("state", unit="flag")) # 0: 0ff, 1: Heating, 2: Cooling, 3: Venting 
        self.add_variable(Variable("T_edb", unit="°C"))
        self.add_variable(Variable("T_ewb", unit="°C"))
        self.add_variable(Variable("F_air", unit="frac"))
        self.add_variable(Variable("F_load", unit="frac"))
        self.add_variable(Variable("F_oa", unit="frac"))
        self.add_variable(Variable("T_supply", unit="°C"))
        self.add_variable(Variable("w_supply", unit="°C"))
        self.add_variable(Variable("Qt_cool", unit="W"))
        self.add_variable(Variable("Qs_cool", unit="W"))
        self.add_variable(Variable("Q_heat", unit="W"))
        self.add_variable(Variable("P_cool", unit="W"))
        self.add_variable(Variable("Pcomp_cool", unit="W"))
        self.add_variable(Variable("Pfan_cool", unit="W"))
        self.add_variable(Variable("Pother_cool", unit="W"))
        self.add_variable(Variable("P_heat", unit="W"))
        self.add_variable(Variable("Pcomp_heat", unit="W"))
        self.add_variable(Variable("Pfan_heat", unit="W"))
        self.add_variable(Variable("Pother_heat", unit="W"))
        self.add_variable(Variable("EER", unit="frac"))
        self.add_variable(Variable("COP", unit="frac"))

         # Sicro
        sicro.SetUnitSystem(sicro.SI)
        self.CP_A = 1007 # (J/kg�K)
        self.DH_W = 2501 # (J/g H20)

    def check(self):
        errors = super().check()
        # Test equipment defined
        if self.parameter("equipment").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, must define its equipment.")
        # Test space defined
        if self.parameter("space").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, must define its space.")
        # Test file_met defined
        if self.parameter("file_met").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, file_met must be defined.")
         # Test outdoor_air_flow
        if self.parameter("outdoor_air_flow").value > self.parameter("supply_air_flow").value:
            errors.append(
                f"Error: {self.parameter('name').value}, outdoor_air_flow must be less than supply_air_flow.")
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._equipment = self.parameter("equipment").component
        self._space = self.parameter("space").component
        self._space_type = self._space.parameter("space_type").component
        self._file_met = self.parameter("file_met").component
        self._supply_air_flow = self.parameter("supply_air_flow").value
        self._outdoor_air_flow = self.parameter("outdoor_air_flow").value
        self._f_air = self._supply_air_flow / self._equipment.parameter("nominal_air_flow").value
        self._f_oa = self._outdoor_air_flow/self._supply_air_flow
        self.ATM_PRESSURE = sicro.GetStandardAtmPressure(self._file_met.altitude)
        self.RHO_A = sicro.GetMoistAirDensity(20,0.0073,self.ATM_PRESSURE)
        self._m_supply =  self.RHO_A * self._supply_air_flow # V_imp * rho 
        self._mrcp =  self.RHO_A * self._supply_air_flow * self.CP_A # V_imp * rho * c_p
        self._mrdh =  self.RHO_A * self._supply_air_flow * self.DH_W # V_imp * rho * Dh
        self._cool_band = self.parameter("cooling_bandwidth").value
        self._heat_band = self.parameter("heating_bandwidth").value

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        self._T_odb = self._file_met.variable("temperature").values[time_index]
        self._T_owb = self._file_met.variable("wet_bulb_temp").values[time_index]
        self._w_o = self._file_met.variable("abs_humidity").values[time_index]
        control_param = self._space.get_control_param(time_index) # T_cool_sp, T_heat_sp, cool_on, heat_on, perfect_conditioning    
        self._T_cool_sp = control_param["T_cool_sp"]
        self._T_heat_sp = control_param["T_heat_sp"]
        self._cool_on = control_param["cool_on"]
        self._heat_on = control_param["heat_on"]
        self._perfect_conditioning = control_param["perfect_conditioning"] 
        self._first_iteration = True
    
    def _mix_air(self, f, T1, w1, T2, w2):
        T = f * T1 + (1-f)*T2
        w = f * w1 + (1-f)*w2
        return (T,w,sicro.GetTWetBulbFromHumRatio(T,w/1000,self.ATM_PRESSURE))
    
    def iteration(self, time_index, date, daylight_saving):
        super().iteration(time_index, date, daylight_saving)
        if (not self._cool_on) and (not self._heat_on): # Off
            self._state = 0
            return True
        else:
            self._T_space = self._space.variable("temperature").values[time_index]
            self._w_space = self._space.variable("abs_humidity").values[time_index]
            # Entering air
            self._T_edb, self._w_e, self._T_ewb = self._mix_air(self._f_oa,self._T_odb,self._w_o,self._T_space,self._w_space)
            if self._perfect_conditioning: # Get load needed by the space
                self._Q_heating = self._space.variable("Q_heating").values[time_index]
                self._Q_cooling = self._space.variable("Q_cooling").values[time_index]
                self.perfect_control()
            else:
                self.termostat_control()
             
             # First iteration not converged
            if self._first_iteration:
                self._first_iteration = False
                return False
            else:
                return True
            
    def perfect_control(self):
        if self._Q_heating > 0:
            heat_cap = self._equipment.get_heating_capacity(self._T_edb, self._T_odb, self._T_owb,self._f_air)
            self._f_load = self._Q_heating/heat_cap
            self._state = 1
            if self._f_load > 1:
                self._Q_res = self._Q_heating - heat_cap 
                self._Q_heating = heat_cap
                self._f_load = 1
            self._T_supply = self._Q_heating / self._mrcp + self._T_edb
            self._w_supply = self._w_e
        elif self._Q_cooling > 0:
            tot_cool_cap, sen_cool_cap = self._equipment.get_cooling_capacity(self._T_edb, self._T_ewb, self._T_odb,self._f_air)
            self._f_load = self._Q_cooling/sen_cool_cap
            self._state = 2
            if self._f_load > 1:
                self._Q_res = self._Q_cooling - sen_cool_cap
                self._Q_cooling = sen_cool_cap
                self._f_load = 1
            self._Q_cooling_tot = tot_cool_cap*self._f_load
            self._T_supply = self._T_edb - self._Q_cooling / self._mrcp
            self._w_supply = self._w_e - (self._Q_cooling_tot - self._Q_cooling) / self._mrdh 
        else:
            self._f_load = 0
            self._state = 3
            self._T_supply = self._T_edb
            self._w_supply = self._w_e 
        self._space.add_system_air_flow({"name": self.parameter("name").value, "V": self._supply_air_flow, "T": self._T_supply, "w": self._w_supply})
                        
    def termostat_control(self):
        self._f_load = 0
        if self._cool_on : # Cooling
            if (self._T_space >= self._T_cool_sp + self._cool_band/2):
                self._f_load = 1
                self._state = 2
            elif (self._T_space <= self._T_cool_sp - self._cool_band/2):
                self._f_load = 0
                self._state = 3
            else:
                self._f_load = (self._T_space - (self._T_cool_sp - self._cool_band/2)) / self._cool_band    
                self._state = 2
        if self._heat_on : # Heating
            if (self._T_space <= self._T_heat_sp - self._heat_band/2):
                self._f_load = 1
                self._state = 1
            elif (self._T_space >= self._T_heat_sp + self._heat_band/2):
                self._f_load = 0
                self._state = 3
            else:
                self._f_load = (self._T_space - (self._T_heat_sp + self._heat_band/2)) / self._heat_band
                self._state = 1
        if self._state == 1: # Heating
            heat_cap = self._equipment.get_heating_capacity(self._T_edb, self._T_odb, self._T_owb,self._f_air)
            self._Q_heating = heat_cap * self._f_load
            self._T_supply = self._Q_heating / self._mrcp + self._T_edb
            self._w_supply = self._w_e
            self._space.add_system_air_flow({"name": self.parameter("name").value, "V": self._supply_air_flow, "T": self._T_supply, "w": self._w_supply})
        elif self._state == 2: # Cooling
            tot_cool_cap, sen_cool_cap = self._equipment.get_cooling_capacity(self._T_edb, self._T_ewb, self._T_odb,self._f_air)
            self._Q_cooling = sen_cool_cap * self._f_load
            self._Q_cooling_tot = tot_cool_cap*self._f_load           
            self._T_supply = self._T_edb - self._Q_cooling / self._mrcp
            self._w_supply = self._w_e - (self._Q_cooling_tot - self._Q_cooling) / self._mrdh 
            self._space.add_system_air_flow({"name": self.parameter("name").value, "V": self._supply_air_flow, "T": self._T_supply, "w": self._w_supply})
        elif self._state == 3: # Venting
            self._T_supply = self._T_edb
            self._w_supply = self._w_e 
            self._space.add_system_air_flow({"name": self.parameter("name").value, "V": self._supply_air_flow, "T": self._T_supply, "w": self._w_supply})

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        self.variable("T_odb").values[time_index] = self._T_odb
        self.variable("T_owb").values[time_index] = self._T_owb
        self.variable("state").values[time_index] = self._state
        if self._state != 0 : # on
            self.variable("T_edb").values[time_index] = self._T_edb
            self.variable("T_ewb").values[time_index] = self._T_ewb
            self.variable("T_supply").values[time_index] = self._T_supply
            self.variable("w_supply").values[time_index] = self._w_supply
            self.variable("F_air").values[time_index] = self._f_air
            self.variable("F_load").values[time_index] = self._f_load
            self.variable("F_oa").values[time_index] = self._f_oa
            if self._state == 1 : # Heating
                self.variable("Q_heat").values[time_index] = self._Q_heating
                comp_power, fan_power, other_power = self._equipment.get_heating_power(self._T_edb,self._T_odb,self._T_owb,self._f_air,self._f_load)
                self.variable("Pcomp_heat").values[time_index] = comp_power
                self.variable("Pfan_heat").values[time_index] = fan_power
                self.variable("Pother_heat").values[time_index] = other_power
                self.variable("P_heat").values[time_index] = comp_power + fan_power + other_power
                self.variable("COP").values[time_index] = self._Q_heating / (comp_power + fan_power + other_power)
            elif self._state == 2 : # Cooling
                self.variable("Qt_cool").values[time_index] = self._Q_cooling_tot
                self.variable("Qs_cool").values[time_index] = self._Q_cooling
                comp_power, fan_power, other_power = self._equipment.get_cooling_power(self._T_edb,self._T_ewb,self._T_odb,self._f_air,self._f_load)
                self.variable("Pcomp_cool").values[time_index] = comp_power
                self.variable("Pfan_cool").values[time_index] = fan_power
                self.variable("Pother_cool").values[time_index] = other_power
                self.variable("P_cool").values[time_index] = comp_power + fan_power + other_power
                self.variable("EER").values[time_index] = self._Q_cooling_tot / (comp_power + fan_power + other_power)    
