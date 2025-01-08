from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_component, Parameter_float, Parameter_boolean
from OpenSimula.Variable import Variable
import numpy as np
import psychrolib as sicro
import math


class Space(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Space"
        self.parameter("description").value = "Indoor building space"
        # Parameters
        self.add_parameter(Parameter_component("space_type", "not_defined", ["Space_type"]))
        self.add_parameter(Parameter_component("building", "not_defined", ["Building"]))
        self.add_parameter(Parameter_float("floor_area", 1, "m²", min=0.0))
        self.add_parameter(Parameter_float("volume", 1, "m³", min=0.0))
        self.add_parameter(Parameter_float("furniture_weight", 10, "kg/m²", min=0.0))
        self.add_parameter(Parameter_float("convergence_DT", 0.01, "°C", min=0.0))
        self.add_parameter(Parameter_float("convergence_Dw", 0.01, "g/kg", min=0.0))

        # Variables
        self.add_variable(Variable("temperature", unit="°C"))
        self.add_variable(Variable("abs_humidity", unit="g/kg"))
        self.add_variable(Variable("rel_humidity", unit="%"))
        self.add_variable(Variable("people_convective", unit="W"))
        self.add_variable(Variable("people_radiant", unit="W"))
        self.add_variable(Variable("people_latent", unit="W"))
        self.add_variable(Variable("light_convective", unit="W"))
        self.add_variable(Variable("light_radiant", unit="W"))
        self.add_variable(Variable("other_gains_convective", unit="W"))
        self.add_variable(Variable("other_gains_radiant", unit="W"))
        self.add_variable(Variable("other_gains_latent", unit="W"))
        self.add_variable(Variable("solar_direct_gains", unit="W"))
        self.add_variable(Variable("infiltration_flow", unit="m³/s"))
        self.add_variable(Variable("surfaces_convective", unit="W"))
        self.add_variable(Variable("delta_int_energy", unit="W"))
        self.add_variable(Variable("infiltration_sensible_heat", unit="W"))
        self.add_variable(Variable("infiltration_latent_heat", unit="W"))
        self.add_variable(Variable("system_sensible_heat", unit="W"))
        self.add_variable(Variable("system_latent_heat", unit="W"))
        self.add_variable(Variable("u_system_sensible_heat", unit="W"))
        self.add_variable(Variable("u_system_latent_heat", unit="W"))

        # Sicro
        sicro.SetUnitSystem(sicro.SI)

    def building(self):
        return self.parameter("building").component

    def check(self):
        errors = super().check()
        # Test building is defined
        if self.parameter("building").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, must define its building.")
        # Test space_type defined
        if self.parameter("space_type").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, must define its Space_type.")
        self._create_surfaces_list()
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._file_met = self.building().parameter("file_met").component
        self._space_type_comp = self.parameter("space_type").component
        self._area = self.parameter("floor_area").value
        self._volume = self.parameter("volume").value
        self._m_furniture = self._area * self.parameter("furniture_weight").value
        self._Dt = self.project().parameter("time_step").value
        self._create_surfaces_list() # surfaces, sides
        self._create_ff_matrix() # ff_matrix
        self._create_dist_vectors() # dsr_dist_vector, ig_dist_vector

    def _create_surfaces_list(self):
        self.surfaces = []
        self.sides = []
        # Exterior
        surfaces_list = self.project().component_list("Exterior_surface")
        for surface in surfaces_list:
            if surface.parameter("space").component == self:
                self.surfaces.append(surface)
                self.sides.append(1)
                for opening in surface.openings:
                    self.surfaces.append(opening)
                    self.sides.append(1)
        # Underground
        surfaces_list = self.project().component_list("Underground_surface")
        for surface in surfaces_list:
            if surface.parameter("space").component == self:
                self.surfaces.append(surface)
                self.sides.append(1)
        # Interior
        surfaces_list = self.project().component_list("Interior_surface")
        for surface in surfaces_list:
            if surface.parameter("spaces").component[0] == self:
                self.surfaces.append(surface)
                self.sides.append(0)
            elif surface.parameter("spaces").component[1] == self:
                self.surfaces.append(surface)
                self.sides.append(1)
        # Virtual Surface
        surfaces_list = self.project().component_list("Virtual_surface")
        for surface in surfaces_list:
            if surface.parameter("spaces").component[0] == self:
                self.surfaces.append(surface)
                self.sides.append(0)
            elif surface.parameter("spaces").component[1] == self:
                self.surfaces.append(surface)
                self.sides.append(1)

    def _coplanar(self, surf1, side1, surf2, side2):
        az_1 = surf1.orientation_angle("azimuth", side1)
        az_2 = surf2.orientation_angle("azimuth", side2)
        alt_1 = surf1.orientation_angle("altitude", side1)
        alt_2 = surf2.orientation_angle("altitude", side2)
        if alt_1 == 90 and alt_2 == 90:  # Two Floors
            return True
        elif alt_1 == -90 and alt_2 == -90:  # Two Roofs
            return True
        else:
            if alt_1 == alt_2 and az_1 == az_2:
                return True
            else:
                return False

    def _create_ff_matrix(self):
        n = len(self.surfaces)
        total_area = 0
        for surf in self.surfaces:
            total_area += surf.area
        self.ff_matrix = np.zeros((n, n))
        seven = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if self._coplanar(self.surfaces[i], self.sides[i], self.surfaces[j], self.sides[j]):
                    seven[i][j] = 0
                else:
                    seven[i][j] = 1
                self.ff_matrix[i][j] = seven[i][j] * \
                    self.surfaces[j].area / total_area
        # iteración
        EPSILON = 1.e-4
        N_MAX_ITER = 500
        n_iter = 0
        residuos = np.ones(n)
        while True:
            n_iter += 1
            residuo_tot = 0
            corregir = False
            for i in range(n):
                residuos[i] = 1.
                for j in range(n):
                    residuos[i] -= self.ff_matrix[i][j]
                if (residuos[i] == 0):
                    residuos[i] = EPSILON/100
                if (math.fabs(residuos[i]) > EPSILON):
                    corregir = True
                    residuo_tot += math.fabs(residuos[i])
            if corregir:
                for i in range(n):
                    for j in range(n):
                        self.ff_matrix[i][j] *= 1 + residuos[i]*residuos[j] * \
                            seven[i][j] / (math.fabs(residuos[i]) +
                                           math.fabs(residuos[j]))
            else:
                break
            if (n_iter > N_MAX_ITER):
                break

    def _create_dist_vectors(self):  # W/m^2 for each surface
        n = len(self.surfaces)
        total_area = 0
        floor_area = 0
        for i in range(n):
            total_area += self.surfaces[i].area
            # Floor
            if self.surfaces[i].orientation_angle("altitude", self.sides[i]) == 90:
                floor_area += self.surfaces[i].area
        self.dsr_dist_vector = np.zeros(n)
        self.ig_dist_vector = np.zeros(n)
        for i in range(n):
            if floor_area > 0:
                # Floor
                if self.surfaces[i].orientation_angle("altitude", self.sides[i]) == 90:
                    self.dsr_dist_vector[i] = 1/floor_area
                else:
                    0
            else:
                self.dsr_dist_vector[i] = 1/total_area
            self.ig_dist_vector[i] = 1/total_area

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        self._first_iteration = True
        # People
        exp = self._space_type_comp.variable("people_convective").values[time_index] 
        self.variable("people_convective").values[time_index] = self._area * exp
        exp = self._space_type_comp.variable("people_latent").values[time_index] 
        self.variable("people_latent").values[time_index] = self._area * exp
        exp = self._space_type_comp.variable("people_radiant").values[time_index]         
        self.variable("people_radiant").values[time_index] = self._area * exp
        # Light
        exp = self._space_type_comp.variable("light_convective").values[time_index]                
        self.variable("light_convective").values[time_index] = self._area * exp
        exp = self._space_type_comp.variable("light_radiant").values[time_index]                
        self.variable("light_radiant").values[time_index] = self._area * exp
        # Other gains
        exp = self._space_type_comp.variable("other_gains_convective").values[time_index]                
        self.variable("other_gains_convective").values[time_index] = self._area * exp
        exp = self._space_type_comp.variable("other_gains_latent").values[time_index]                
        self.variable("other_gains_latent").values[time_index] = self._area * exp
        exp = self._space_type_comp.variable("other_gains_radiant").values[time_index]                
        self.variable("other_gains_radiant").values[time_index] = self._area * exp
        # Infiltration
        exp = self._space_type_comp.variable("infiltration_rate").values[time_index]     
        V_inf = self._volume * exp / 3600          
        self.variable("infiltration_flow").values[time_index] = V_inf
        # Systems air flows
        self.uncontrol_systems = []
        self.control_system = {"V": 0, "T": 0, "w":0, "Q": 0, "M": 0} # V (m^3/s), T (°C), w (g/kg), Q (W), M (gr H2O)
        # Initial values
        self._estimate_T_w(time_index)
        # Humidity balance
        rho = self.building().RHO
        lam = self.building().LAMBDA
        self._K_hum = rho * (self._volume / self._Dt + V_inf)
        self._F_hum = (self.variable("people_latent").values[time_index] + self.variable("other_gains_latent").values[time_index])/lam
        self._F_hum += rho * self._volume / self._Dt * self._w_pre + rho * V_inf * self._file_met.variable("abs_humidity").values[time_index]
       
    def _estimate_T_w(self, time_i):
        if time_i == 0:
            self._T_pre = self.building().parameter("initial_temperature").value
            self._w_pre = self.building().parameter("initial_humidity").value
        else:
            self._T_pre = self.variable("temperature").values[time_i-1]
            self._w_pre = self.variable("abs_humidity").values[time_i-1]
        self.variable("temperature").values[time_i] = self._T_pre
        self.variable("abs_humidity").values[time_i] = self._w_pre
        self._T = self._T_pre
        self._w = self._w_pre

    def iteration(self, time_index, date, daylight_saving):
        super().iteration(time_index, date, daylight_saving)
        # Calculate shadows only once
        if self._first_iteration:
            self._calculate_solar_direct_gains(time_index)
            self._first_iteration = False
            return False
        else:
            self.variable("temperature").values[time_index] = self._calculate_T(True)["T"]
            w = self._calculate_w(True)["w"]
            max_hum = sicro.GetHumRatioFromRelHum(self.variable("temperature").values[time_index], 1, self.building().ATM_PRESSURE)*1000
            if (w > max_hum):
                self.variable("abs_humidity").values[time_index] = max_hum
            else:
                self.variable("abs_humidity").values[time_index] = w
            # Test convergence
            return self._converged(time_index)

    def _calculate_solar_direct_gains(self, time_i):
        solar_gain = 0
        for surf in self.surfaces:
            if surf.parameter("type").value == "Opening":
                solar_gain += surf.area * surf.variable("E_dir_tra").values[time_i]

        self.variable("solar_direct_gains").values[time_i] = solar_gain

    def update_K_F(self, K_F):
        self.K_F = K_F

    def _acumulate_u_systems(self):
        self._V_u_systems = 0
        self._V_T_u_systems = 0
        self._V_w_u_systems = 0
        for system in self.uncontrol_systems:
            self._V_u_systems += system["V"]
            self._V_T_u_systems += system["V"]*system["T"]
            self._V_w_u_systems += system["V"]*system["w"]

    def _calculate_T(self, control):
        rho = self.building().RHO
        c_p = self.building().C_P
        self._acumulate_u_systems()
        F_tot = self.K_F["F"]+self.K_F["F_OS"] + self._V_T_u_systems * rho * c_p
        K_tot = self.K_F["K"] + self._V_u_systems * rho * c_p
        if control:
            K_tot += self.control_system["V"]*rho*c_p
            F_tot += self.control_system["V"]*rho*c_p*self.control_system["T"] + self.control_system["Q"]
        return {"T": F_tot/ K_tot, "K": K_tot, "F": F_tot}

    def _calculate_w(self, control):
        rho = self.building().RHO
        self._acumulate_u_systems()
        K_hum = self._K_hum + rho * self._V_u_systems
        F_hum = self._F_hum + rho * self._V_w_u_systems
        if control:
            K_hum += self.control_system["V"]*rho
            F_hum += self.control_system["V"]*rho*self.control_system["w"]  + self.control_system["M"]
        return {"w": F_hum/K_hum , "K": K_hum, "F": F_hum}

    def _converged(self, time_i):
        converged = True
        if abs(self._T -self.variable("temperature").values[time_i]) > self.parameter("convergence_DT").value:
            converged = False
        if abs(self._w -self.variable("abs_humidity").values[time_i]) > self.parameter("convergence_Dw").value:
            converged = False
        self._T = self.variable("temperature").values[time_i]
        self._w = self.variable("abs_humidity").values[time_i] 
        return converged

    def get_Q_required(self, T_cool_sp, T_heat_sp):
        dic =  self._calculate_T(False)
        if dic["T"] > T_cool_sp:
            return dic["K"]*T_cool_sp - dic["F"]
        elif dic["T"] < T_heat_sp:
             return dic["K"]*T_heat_sp - dic["F"]
        else:
            return 0
    
    def get_M_required(self,HR_min, HR_max):
        dic = self._calculate_w(False)
        hr = sicro.GetRelHumFromHumRatio(self._T, dic["w"]/1000, self.building().ATM_PRESSURE)*100
        if hr < HR_min:
            w_min = sicro.GetHumRatioFromRelHum(self._T, HR_min/100, self.building().ATM_PRESSURE)*1000
            return dic["K"] * w_min - dic["F"]
        elif hr > HR_max:
            w_max = sicro.GetHumRatioFromRelHum(self._T, HR_max/100, self.building().ATM_PRESSURE)*1000
            return dic["K"] * w_max - dic["F"]
        else:
            return 0

    def add_uncontrol_system_air_flow(self,air_flow):
        # Delete if exist
        self.uncontrol_systems = [air for air in self.uncontrol_systems if air['name'] != air_flow["name"] ]
        # Append
        self.uncontrol_systems.append(air_flow)
    
    def set_control_system(self,system_dic):
        self.control_system = system_dic

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        rh = sicro.GetRelHumFromHumRatio(self._T, self._w/1000, self.building().ATM_PRESSURE)*100
        self.variable("rel_humidity").values[time_index] = rh
        self._calculate_heat_fluxes(time_index)

    def _calculate_heat_fluxes(self, time_i):
        rho = self.building().RHO
        c_p = self.building().C_P
        c_pf = self.building().C_P_FURNITURE
        lam = self.building().LAMBDA
        V_inf = self.variable("infiltration_flow").values[time_i]
        T_ext = self._file_met.variable("temperature").values[time_i]
        w_ext = self._file_met.variable("abs_humidity").values[time_i]

        # Sensibles
        self.variable("delta_int_energy").values[time_i] = ( self._volume * rho * c_p + self._m_furniture * c_pf) * (self._T - self._T_pre) / self._Dt
        self.variable("infiltration_sensible_heat").values[time_i] = V_inf * rho * c_p * (T_ext - self._T)
        self.variable("u_system_sensible_heat").values[time_i] = rho * c_p * (self._V_T_u_systems - self._V_u_systems * self._T)
        Q = self.control_system["V"]*rho*c_p*(self.control_system["T"] - self._T) + self.control_system["Q"]
        self.variable("system_sensible_heat").values[time_i] = Q

        Q_rest =  self.variable("delta_int_energy").values[time_i] 
        - self.variable("people_convective").values[time_i]
        - self.variable("light_convective").values[time_i]
        - self.variable("other_gains_convective").values[time_i]
        - self.variable("infiltration_sensible_heat").values[time_i]
        - self.variable("u_system_sensible_heat").values[time_i]
        - Q

        self.variable("surfaces_convective").values[time_i] = Q_rest
        
        # Latents
        self.variable("infiltration_latent_heat").values[time_i] = V_inf * rho * lam * (w_ext - self._w)
        self.variable("u_system_latent_heat").values[time_i] = rho * lam * (self._V_w_u_systems - self._V_u_systems * self._w)
        self.variable("system_latent_heat").values[time_i] = self.control_system["V"]*rho*lam*(self.control_system["w"] - self._w) + self.control_system["M"]*lam

