from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_component,
    Parameter_float,
    Parameter_float_list,
    Parameter_variable_list,
    Parameter_math_exp,
    Parameter_options,
)
from opensimula.Component import Component
from opensimula.Variable import Variable
from opensimula.Iterative_process import Iterative_process

class HVAC_water_system(Component):  # HVAC Water system
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_water_system"
        self.parameter("description").value = "HVAC Water System"
        self.add_parameter(
            Parameter_component("water_thermal_generator", "not_defined", ["Chiller_heat_pump"])
        )
        self.add_parameter(
            Parameter_component("pump", "not_defined", ["Pump"])
        )
        self.add_parameter(Parameter_float("design_water_flow", 1, "dm³/s", min=0))
        self.add_parameter(Parameter_float("initial_water_temp", 20, "°C"))
        self.add_parameter(Parameter_float("total_water_volume", 1, "m³", min=0))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("heating_water_setpoint", "45", "°C"))
        self.add_parameter(Parameter_math_exp("cooling_water_setpoint", "7", "°C"))
        self.add_parameter(Parameter_math_exp("system_on_off", "1", "on/off"))
        self.add_parameter(
            Parameter_options("pump_operation", "ALLWAYS_ON", ["ALLWAYS_ON", "ON_COIL_LOAD"])
        )
        self.add_parameter(
            Parameter_options("system_mode", "COILS_CONTROL", ["COILS_CONTROL", "SCHEDULE_CONTROL"])
        )
        self.add_parameter(Parameter_math_exp("cooling_mode", "1", "on/off"))
        self.add_parameter(Parameter_math_exp("heating_mode", "1", "on/off"))
        self.add_parameter(Parameter_math_exp("Q_loss_expression", "0", "W"))
        self.add_parameter(Parameter_float("convergence_DT", 0.01, "°C", min=0.0))
        self.add_parameter(Parameter_float_list("water_limits", [1, 99], "°C", min=0, max=100))

        # Variables
        self.add_variable(
            Variable("state", unit="flag")
        )  # 0: 0ff, 1: Heating, -1:Cooling, 2: Standby
        self.add_variable(Variable("T_WGO", unit="°C"))
        self.add_variable(Variable("T_WGI", unit="°C"))
        self.add_variable(Variable("T_WCI", unit="°C"))
        self.add_variable(Variable("T_WCO", unit="°C"))
        self.add_variable(Variable("T_WAVG", unit="°C"))
        self.add_variable(Variable("water_flow", unit="m³/s"))
        self.add_variable(Variable("Q_gen", unit="W"))
        self.add_variable(Variable("Q_coils", unit="W"))
        self.add_variable(Variable("Q_loss", unit="W"))
        self.add_variable(Variable("Q_pump", unit="W"))
        self.add_variable(Variable("delta_U", unit="W"))
        self.add_variable(Variable("pump_power", unit="W"))
        self.add_variable(Variable("generator_power", unit="W"))
        self.add_variable(Variable("generator_efficiency", unit="-"))
        self.add_variable(Variable("generator_part_load", unit="frac"))
        self.add_variable(Variable("heating_water_setpoint", unit="°C"))
        self.add_variable(Variable("cooling_water_setpoint", unit="°C"))

    def check(self):
        errors = super().check()
        # Test generator defined
        if (
            self.parameter("water_thermal_generator").value == "not_defined"
        ):
            msg = f"{self.parameter('name').value}, must define one water thermal generator."
            errors.append(Message(msg, "ERROR"))
        # Test pump defined
        if self.parameter("pump").value == "not_defined":
            msg = (
                f"{self.parameter('name').value}, must define its pump."
            )
            errors.append(Message(msg, "ERROR"))
        # Test file_met defined
        if self.project().parameter("simulation_file_met").value == "not_defined":
            msg = f"{self.parameter('name').value}, file_met must be defined in the project 'simulation_file_met'."
            errors.append(Message(msg, "ERROR"))
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self.props = self._sim_.props
        self.delta_t = delta_t
        self.file_met = self.project().parameter("simulation_file_met").component
        # Parameters
        self.generator = self.parameter("water_thermal_generator").component
        self.pump = self.parameter("pump").component
        self.water_flow = self.parameter("design_water_flow").value
        self.min_water_temp = self.parameter("water_limits").value[0]
        self.max_water_temp = self.parameter("water_limits").value[1]

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        # Outdoor air
        self.T_OA = self.file_met.variable("temperature").values[time_index]
        self.T_OAwb = self.file_met.variable("wet_bulb_temp").values[time_index]
        # Temperatures initial values
        if time_index == 0:
            self.T_WGO_pre = self.parameter("initial_water_temp").value
            self.T_WGI_pre = self.parameter("initial_water_temp").value
            self.T_WCI_pre = self.parameter("initial_water_temp").value
            self.T_WCO_pre = self.parameter("initial_water_temp").value
        else:
            self.T_WGO_pre = self.variable("T_WGO").values[time_index-1]
            self.T_WGI_pre = self.variable("T_WGI").values[time_index-1]
            self.T_WCI_pre = self.variable("T_WCI").values[time_index-1]
            self.T_WCO_pre = self.variable("T_WCO").values[time_index-1]
        # Water mass flow
        self.water_flow = self.parameter("design_water_flow").value/1000  # Convert from dm³/s to m³/s
        self.variable("water_flow").values[time_index] = self.water_flow
        T_avg_pre = (self.T_WGO_pre + self.T_WGI_pre + self.T_WCI_pre + self.T_WCO_pre)/4
        self.m_rho_cp = self.props["RHOCP_W"](T_avg_pre) * self.water_flow
        self.V_rho_cp = self.parameter("total_water_volume").value * self.props["RHOCP_W"](T_avg_pre)
        self.T_WCI = self.T_WCI_pre
        self.T_WGO = self.T_WGO_pre

        # variables dictonary
        self.var_dic = self.get_parameter_variable_dictionary(time_index)
        self.var_dic["T_w"] = T_avg_pre
        self.Q_loss = self.parameter("Q_loss_expression").evaluate(self.var_dic)

        # setpoints
        self.T_heat_sp = self.parameter("heating_water_setpoint").evaluate(self.var_dic)
        self.variable("heating_water_setpoint").values[time_index] = self.T_heat_sp
        self.T_cool_sp = self.parameter("cooling_water_setpoint").evaluate(self.var_dic)
        self.variable("cooling_water_setpoint").values[time_index] = self.T_cool_sp

        # on/off
        self.on_off = self.parameter("system_on_off").evaluate(self.var_dic)
        # Q_coils load
        self.Q_coils = 0
        self.pre_iter = True 
        # Q_pump
        self.Q_pump = self.pump.get_heat_gain(self.water_flow)
        # Iterative 
        self.itera_T = Iterative_process(self.T_WGO_pre,tol=self.parameter("convergence_DT").value,n_ini_relax=3,rel_vel=0.8)
        # Control mode
        if self.parameter("system_mode").value == "SCHEDULE_CONTROL":
            varibles_dic = self.get_parameter_variable_dictionary(time_index)
            cooling_mode = self.parameter("cooling_mode").evaluate(varibles_dic)
            heating_mode = self.parameter("heating_mode").evaluate(varibles_dic)
            self.mode = 0
            if cooling_mode == 1:
                self.mode = -1
            if heating_mode == 1:
                self.mode = 1
           
    def get_cooling_coil_inlet_T(self):
        if self.pre_iter: 
            return self.T_cool_sp
        else:
            return self.T_WCI


    def get_heating_coil_inlet_T(self):
        if self.pre_iter: 
            return self.T_heat_sp
        else:
            return self.T_WCI

    def add_coil_load(self, Q_coil):
        self.Q_coils += Q_coil

    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)
        self.pre_iter = False
        self._check_state()
        if self.state == 0: # System off
            delta_T = (-self.Q_loss-self.Q_coils)*self.delta_t/(self.parameter("total_water_volume").value * self.props["RHOCP_W"](self.T_WGO))
            self.T_WGO = self.T_WGO_pre + delta_T
        else:
            self.delta_U = self.V_rho_cp * (self.T_WGO - self.T_WGO_pre)/self.delta_t
            Q = self.Q_coils + self.Q_loss - self.Q_pump 
            self.Q_gen_required = Q + self.delta_U
            self.T_WGO_FF =-Q*self.delta_t/(self.V_rho_cp)+self.T_WGO_pre
            self._simulate_generator()            
        # Resto de temperaturas
        self.T_WGO = self.itera_T.estimate_next_x(self.T_WGO)        
        self.T_WCI = self.T_WGO - (self.Q_loss/2)/self.m_rho_cp
        self.T_WCO = self.T_WCI - (self.Q_coils)/self.m_rho_cp
        self.T_WGI = self.T_WCO - (self.Q_loss/2)/self.m_rho_cp            
        # Update Q_loss
        self.T_avg = (self.T_WGO+self.T_WGI+self.T_WCI+self.T_WCO)/4
        self.var_dic["T_w"] = self.T_avg
        self.Q_loss = self.parameter("Q_loss_expression").evaluate(self.var_dic)
        # Colocar de nuevo Q_coils = 0 al inicio de cada iteración.
        self.Q_coils = 0
        # Test convergence
        return self.itera_T.converged() 

    def _check_state(self):
        if self.on_off:
            if self.parameter("system_mode").value == "SCHEDULE_CONTROL":
                if self.mode == 0:
                    if self.parameter("pump_operation").value == "ALLWAYS_ON":
                        self.state = 2
                    elif self.parameter("pump_operation").value == "ON_COIL_LOAD":
                        self.state = 0
                elif self.mode == 1:
                    if self.parameter("pump_operation").value == "ON_COIL_LOAD" and self.Q_coils <= 0:
                        self.state = 0
                    else:
                        self.state = 1
                elif self.mode == -1:
                    if self.parameter("pump_operation").value == "ON_COIL_LOAD" and self.Q_coils >= 0:
                        self.state = 0
                    else:   
                        self.state = -1
            elif self.parameter("system_mode").value == "COILS_CONTROL":
                if self.Q_coils > 0:
                    self.state = 1 
                elif self.Q_coils < 0:
                    self.state = -1
                else:
                    if self.parameter("pump_operation").value == "ALLWAYS_ON":
                        self.state = 2
                    elif self.parameter("pump_operation").value == "ON_COIL_LOAD":
                        self.state = 0
        else:
            self.state = 0

    def _simulate_generator(self):
        if self.state == 1 and self.T_WGO_FF < self.T_heat_sp: # Heating
            self.T_WGO = self.T_heat_sp
            self.Q_gen, self.f_load = self.generator.get_heating_load(self.T_WGO, self.T_OA, self.T_OAwb, self.water_flow, self.Q_gen_required)
            if self.f_load == 1 or self.f_load == 0: # Not enough heating power, update T_WGO with the actual Q_gen
                delta_T = (self.Q_gen+self.Q_pump-self.Q_coils-self.Q_loss)*self.delta_t/self.V_rho_cp
                self.T_WGO = self.T_WGO_pre + delta_T
        elif self.state == -1 and self.T_WGO_FF > self.T_cool_sp: # Cooling
            self.T_WGO = self.T_cool_sp
            self.Q_gen, self.f_load = self.generator.get_cooling_load(self.T_WGO, self.T_OA, self.T_OAwb, self.water_flow, -self.Q_gen_required)
            self.Q_gen = -self.Q_gen
            if self.f_load == 1 or self.f_load == 0: # Not enough cooling power, update T_WGO with the actual Q_gen
                delta_T = (self.Q_gen+self.Q_pump-self.Q_coils-self.Q_loss)*self.delta_t/self.V_rho_cp
                self.T_WGO = self.T_WGO_pre + delta_T
        else:
            self.T_WGO = self.T_WGO_FF
            self.Q_gen = 0

    def limit_water_temperature(self, T):
        if T > self.max_water_temp:
            return self.max_water_temp
        elif T < self.min_water_temp:
            return self.min_water_temp
        else:   
            return T

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        self.variable("state").values[time_index] = self.state
        self.variable("T_WGO").values[time_index] = self.limit_water_temperature(self.T_WGO)
        self.variable("T_WGI").values[time_index] = self.limit_water_temperature(self.T_WGI)
        self.variable("T_WCO").values[time_index] = self.limit_water_temperature(self.T_WCO)
        self.variable("T_WCI").values[time_index] = self.limit_water_temperature(self.T_WCI)
        self.variable("T_WAVG").values[time_index] = self.limit_water_temperature(self.T_avg)
        if self.state == 0:
            self.variable("Q_gen").values[time_index] = 0
            self.variable("Q_coils").values[time_index] = 0
            self.variable("Q_pump").values[time_index] = 0
            self.variable("pump_power").values[time_index] = 0
            self.variable("generator_power").values[time_index] = 0
            self.variable("generator_efficiency").values[time_index] = 0
            self.variable("generator_part_load").values[time_index] = 0
        else:
            self.variable("Q_gen").values[time_index] = self.Q_gen
            self.variable("Q_coils").values[time_index] = self.Q_coils
            self.variable("Q_pump").values[time_index] = self.Q_pump
            self.variable("pump_power").values[time_index] = self.pump.get_power(self.water_flow)
            if self.state == 1:
                power, eff = self.generator.get_heating_power(self.T_WGO, self.T_OA, self.T_OAwb, self.water_flow, self.Q_gen_required)
            elif self.state == -1:  
                power, eff = self.generator.get_cooling_power(self.T_WGO, self.T_OA, self.T_OAwb, self.water_flow, self.Q_gen_required)
            elif self.state == 2:
                power = 0
                eff = 0
                self.f_load = 0
            self.variable("generator_power").values[time_index] = power
            self.variable("generator_efficiency").values[time_index] = eff
            self.variable("generator_part_load").values[time_index] = self.f_load            
        self.variable("Q_loss").values[time_index] = self.Q_loss
        self.variable("delta_U").values[time_index] = self.V_rho_cp * (self.T_WGO - self.T_WGO_pre)/self.delta_t
