from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_component,
    Parameter_float,
    Parameter_variable_list,
    Parameter_math_exp
)
from opensimula.Component import Component
from opensimula.Variable import Variable


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
        self.add_parameter(Parameter_float("design_water_flow", 1, "m³/s", min=0))
        self.add_parameter(Parameter_float("initial_water_temp", 20, "°C"))
        self.add_parameter(Parameter_float("total_water_volume", 1, "m³", min=0))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("heating_water_setpoint", "45", "°C"))
        self.add_parameter(Parameter_math_exp("cooling_water_setpoint", "7", "°C"))
        self.add_parameter(Parameter_math_exp("system_on_off", "1", "on/off"))
        self.add_parameter(Parameter_math_exp("Q_loss_expression", "0", "W"))

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
        self.file_met = self.project().parameter("simulation_file_met").component
        # Parameters
        self.generator = self.parameter("water_thermal_generator").component
        self.pump = self.parameter("pump").component
        self.water_flow = self.parameter("design_water_flow").value

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        # Outdoor air
        self.T_OA = self.file_met.variable("temperature").values[time_index]
        self.T_OAwb = self.file_met.variable("wet_bulb_temp").values[time_index]
        # Temperatures initial values
        if time_index == 0:
            self.T_wavg_pre = self.parameter("initial_water_temp").value
            self.T_WGO_pre = self.parameter("initial_water_temp").value
            self.T_WGI_pre = self.parameter("initial_water_temp").value
            self.T_WCI_pre = self.parameter("initial_water_temp").value
            self.T_WCO_pre = self.parameter("initial_water_temp").value
        else:
            self.T_wavg_pre = self.variable("T_WAVG").values[time_index-1]
            self.T_WGO_pre = self.variable("T_WGO").values[time_index-1]
            self.T_WGI_pre = self.variable("T_WGI").values[time_index-1]
            self.T_WCI_pre = self.variable("T_WCI").values[time_index-1]
            self.T_WCO_pre = self.variable("T_WCO").values[time_index-1]
        self.T_WCI = self.T_WCI_pre # For coils inlet temperature, we consider the previous iteration value, as the coils are before the pump and generator in the water circuit
        # Water mass flow
        self.water_flow = self.parameter("design_water_flow").value
        self.variable("water_flow").values[time_index] = self.water_flow

        # variables dictonary
        self.var_dic = self.get_parameter_variable_dictionary(time_index)
        self.var_dic["T_wavg"] = self.T_wavg_pre
        self.Q_loss = self.parameter("Q_loss_expression").evaluate(self.var_dic)

        # setpoints
        self.T_heat_sp = self.parameter("heating_water_setpoint").evaluate(self.var_dic)
        self.variable("heating_water_setpoint").values[time_index] = self.T_heat_sp
        self.T_cool_sp = self.parameter("cooling_water_setpoint").evaluate(self.var_dic)
        self.variable("cooling_setpoint").values[time_index] = self.T_cool_sp

        # on/off
        self.on_off = self.parameter("system_on_off").evaluate(self.var_dic)
        if self.on_off == 0:
            self.state = 0
            self.variable("state").values[time_index] = 0
            self.on_off = False
        else:
            self.on_off = True
        # Q_coils load
        self.Q_coils = 0
        # Q_pump
        self.Q_pump = self.pump.get_heat_gain(self.water_flow)
        # Q_gen_iter
        self.Q_gen_iter = 0


    def get_coil_inlet_T(self):
        return self.T_WCI
    
    def add_coil_load(self, Q_coil):
        self.Q_coils += Q_coil

### Por aquí ...

    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)
        if self.on_off: 
            self._calculate_Q_required()
            self._get_Q_gen()
            self._check_Q_gen()
            # Colocar de nuevo Q_coils = 0 al inicio de cada iteración, para evitar que se acumule el efecto de las cargas en las iteraciones
            self.Q_coils = 0
            # Update Q_loss
            self.var_dic["T_wavg"] = self.T_wavg
            self.Q_loss = self.parameter("Q_loss_expression").evaluate(self.var_dic)

            # If Q_gen_iter == Q_gen, then we have convergence in the generator, if not, we need to iterate again
            if (self.Q_gen_iter == self.Q_gen):
                return True
            else:   
                self.Q_gen_iter = self.Q_gen    
                return False
        else:               
            delta_T = (-self.Q_loss)*self.delta_t/(self.parameter("total_water_volume").value * self.props["RHOCP_W"](self.T_wavg))
            self.T_WGO = self.T_WGO_pre + delta_T
            self.T_WCI = self.T_WGI_pre + delta_T
            self.T_WCO = self.T_WCO_pre + delta_T
            self.T_WGI = self.T_WGI_pre + delta_T
            self.T_wavg = (self.T_WGI + self.T_WGO+self.T_WCI+self.T_WCO)/4
            # Update Q_loss
            Q_loss_iter = self.Q_loss
            self.var_dic["T_wavg"] = self.T_wavg
            self.Q_loss = self.parameter("Q_loss_expression").evaluate(self.var_dic)
            if (Q_loss_iter == self.Q_loss):
                return True
            else:   
                return False

    def _calculate_Q_required(self):
        delta_U = self.parameter("total_water_volume").value * self.props["RHOCP_W"](self.T_wavg) * (self.T_wavg - self.T_wavg_pre)/self.delta_t
        self.Q_gen_required = self.Q_coils + self.Q_loss - self.Q_pump + delta_U
        
    def _get_Q_gen(self):
        if self.Q_gen_required >= 0: # Heating
            self.state = 1
            self.T_WGO = self.T_heat_sp
            self.Q_gen, self.f_load = self.generator.get_heating_load(self.T_WGO, self.T_OA, self.T_OAwb, self.water_flow, self.Q_gen_required)
        elif self.Q_gen_required < 0: # Cooling
            self.state = -1
            self.T_WGO = self.T_cool_sp
            self.Q_gen, self.f_load = self.generator.get_cooling_load(self.T_WGO, self.T_OA, self.T_OAwb, self.water_flow, -self.Q_gen_required)
            self.Q_gen = -self.Q_gen
    
    def _check_Q_gen(self):
        if self.Q_gen_required >= 0: # Heating
            if self.Q_gen < self.Q_gen_required:
                delta_T = (self.Q_gen+self.Q_pump-self.Q_coils-self.Q_loss)*self.delta_t/(self.parameter("total_water_volume").value * self.props["RHOCP_W"](self.T_wavg))
                self.T_WGO = self.T_WGO_pre + delta_T
        elif self.Q_gen_required < 0: # Cooling
            if -self.Q_gen < -self.Q_gen_required:
                delta_T = (self.Q_gen+self.Q_pump-self.Q_coils-self.Q_loss)*self.delta_t/(self.parameter("total_water_volume").value * self.props["RHOCP_W"](self.T_wavg))
                self.T_WGO = self.T_WGO_pre + delta_T
        # Resto de temperaturas
        mrho_cp = self.props["RHOCP_W"](self.T_wavg) * self.water_flow
        self.T_WCI = self.T_WGO - (self.Q_loss/2)/mrho_cp
        self.T_WCO = self.T_WCI - (self.Q_coils)/mrho_cp
        self.T_WGI = self.T_WCO - (self.Q_loss/2)/mrho_cp
        self.T_wavg = (self.T_WGI + self.T_WGO+self.T_WCI+self.T_WCO)/4



    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        self.variable("state").values[time_index] = self.state
        self.variable("T_WGO").values[time_index] = self.T_WGO
        self.variable("T_WGI").values[time_index] = self.T_WGI
        self.variable("T_WCO").values[time_index] = self.T_WCO        
        self.variable("T_WCI").values[time_index] = self.T_WCI
        self.variable("T_WAVG").values[time_index] = self.T_wavg
        if self.on_off: 
            self.variable("Q_gen").values[time_index] = self.Q_gen
            self.variable("Q_coils").values[time_index] = self.Q_coils
            self.variable("Q_pump").values[time_index] = self.Q_pump
            self.variable("pump_power").values[time_index] = self.pump.get_power(self.water_flow)
            if self.state == 1:
                power, eff = self.generator.get_heating_power(self.T_WGO, self.T_OA, self.T_OAwb, self.water_flow, self.Q_gen_required)
            elif self.state == -1:  
                power, eff = self.generator.get_cooling_power(self.T_WGO, self.T_OA, self.T_OAwb, self.water_flow, self.Q_gen_required)
            self.variable("generator_power").values[time_index] = power
            self.variable("generator_efficiency").values[time_index] = eff
            self.variable("generator_part_load").values[time_index] = self.f_load
        else:
            self.variable("Q_gen").values[time_index] = 0
            self.variable("Q_coils").values[time_index] = 0
            self.variable("Q_pump").values[time_index] = 0
            self.variable("pump_power").values[time_index] = 0
            self.variable("generator_power").values[time_index] = 0
            self.variable("generator_efficiency").values[time_index] = 0
            self.variable("generator_part_load").values[time_index] = 0
        self.variable("Q_loss").values[time_index] = self.Q_loss
        self.variable("delta_U").values[time_index] = self.parameter("total_water_volume").value * self.props["RHOCP_W"](self.T_wavg) * (self.T_wavg - self.T_wavg_pre)/self.delta_t
