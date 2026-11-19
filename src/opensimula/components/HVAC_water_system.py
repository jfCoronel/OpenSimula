from opensimula.Component import Component  # noqa: N999
from opensimula.Iterative_process import Iterative_process
from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_component_list,
    Parameter_float,
    Parameter_float_list,
    Parameter_math_exp,
    Parameter_options,
    Parameter_variable_list,
)
from opensimula.Variable import Variable


class HVAC_water_system(Component):  # HVAC Water system
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_water_system"
        self.parameter("description").value = "HVAC Water System"
        self.add_parameter(
            Parameter_component_list("generators", ["not_defined"], ["HVAC_water_generator"])
        )
        # PRIORITY: in the order of the list, the next one when the previous is at full
        # load; EQUAL_LOAD: all those able to run at the same part load
        self.add_parameter(Parameter_options("sequencing", "PRIORITY", ["PRIORITY", "EQUAL_LOAD"]))
        # Secondary pumps: with them the plant has a header (primary / secondary)
        self.add_parameter(Parameter_component_list("pumps", [], ["Pump"]))
        self.add_parameter(Parameter_float("initial_water_temp", 20, "°C"))
        self.add_parameter(Parameter_float("total_water_volume", 1000, "dm³", min=0))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("heating_water_setpoint", "45", "°C"))
        self.add_parameter(Parameter_math_exp("cooling_water_setpoint", "7", "°C"))
        self.add_parameter(Parameter_math_exp("system_on_off", "1", "on/off"))
        self.add_parameter(
            Parameter_options("pump_operation", "ALLWAYS_ON", ["ALLWAYS_ON", "ON_LOAD"]) # ALLWAYS_ON: pump on when system is on, ON_LOAD: pump on when heating or cooling load is required
        )
        self.add_parameter(
            Parameter_options("system_control", "LOAD_CONTROL", ["LOAD_CONTROL", "SCHEDULE_CONTROL"]) # LOAD_CONTROL: system cooling/heating based on load, SCHEDULE_CONTROL: system cooling based on cooling_mode and heating based on heating_mode
        )
        self.add_parameter(Parameter_math_exp("system_mode", "1", "-1/0/1")) # -1: Cooling, 0: Standby, 1: Heating only used when system_control = SCHEDULE_CONTROL
        self.add_parameter(Parameter_math_exp("Q_loss", "0", "W"))
        self.add_parameter(Parameter_float("convergence_DT", 0.01, "°C", min=0.0))
        self.add_parameter(Parameter_float_list("water_limits", [1, 99], "°C", min=0, max=100))
        self.add_parameter(Parameter_math_exp("Q_process", "0", "W"))

        # Variables
        self.add_variable(Variable("on_off", unit="flag"))  # 0: 0ff, 1: on
        self.add_variable(Variable("mode", unit="flag"))  # 0: 0ff, 1: Heating, -1:Cooling, 2: Standby
        self.add_variable(Variable("T_generators_out", unit="°C"))
        self.add_variable(Variable("T_generators_in", unit="°C"))
        self.add_variable(Variable("T_supply", unit="°C"))
        self.add_variable(Variable("T_return", unit="°C"))
        self.add_variable(Variable("T_mean", unit="°C"))
        self.add_variable(Variable("coils_flow", unit="dm³/s"))
        self.add_variable(Variable("primary_flow", unit="dm³/s"))
        self.add_variable(Variable("secondary_flow", unit="dm³/s"))
        self.add_variable(Variable("bypass_flow", unit="dm³/s"))
        self.add_variable(Variable("Q_generators", unit="W"))
        self.add_variable(Variable("Q_coils", unit="W"))
        self.add_variable(Variable("Q_process", unit="W"))
        self.add_variable(Variable("Q_loss", unit="W"))
        self.add_variable(Variable("Q_pump", unit="W"))
        self.add_variable(Variable("delta_U", unit="W"))
        self.add_variable(Variable("pumps_power", unit="W"))
        self.add_variable(Variable("secondary_pumps_power", unit="W"))
        self.add_variable(Variable("generators_power", unit="W"))
        self.add_variable(Variable("generators_fuel_power", unit="W"))
        self.add_variable(Variable("electric_power", unit="W"))  # generators and pumps
        self.add_variable(Variable("heating_water_setpoint", unit="°C"))
        self.add_variable(Variable("cooling_water_setpoint", unit="°C"))

    def check(self):
        errors = super().check()
        # Test generators defined
        generators = self.parameter("generators").value
        if len(generators) == 0 or any(g == "not_defined" for g in generators):
            msg = f"{self.parameter('name').value}, must define its generators (HVAC_water_generator)."
            errors.append(Message(msg, "ERROR"))
        # Test file_met defined
        if self.project().parameter("simulation_file_met").value == "not_defined":
            msg = f"{self.parameter('name').value}, file_met must be defined in the project 'simulation_file_met'."
            errors.append(Message(msg, "ERROR"))
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self.props = self._sim_.props # Fluid properties
        self.delta_t = delta_t
        self.file_met = self.project().parameter("simulation_file_met").component
        # Parameters
        self.generators = self.parameter("generators").component
        self.sequencing = self.parameter("sequencing").value
        # The loop is moved by the pumps of the generators (in parallel), that can be
        # not defined (Q_pump = 0)
        self.pump = next((g.get_pump() for g in self.generators if g.get_pump() is not None), None)
        self.design_water_flow = sum(g.nominal_water_flow() for g in self.generators)
        # Header: the secondary pumps move the water to the coils, the primary pumps of
        # the generators only that of the generators running
        self.secondary_pumps = self.parameter("pumps").component
        self.has_header = len(self.secondary_pumps) > 0
        self.secondary_design_flow = sum(
            p.parameter("nominal_water_flow").value for p in self.secondary_pumps
        )
        self.running_pre = [True] + [False] * (len(self.generators) - 1)
        self.min_water_temp = self.parameter("water_limits").value[0]
        self.max_water_temp = self.parameter("water_limits").value[1]

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        # Temperatures initial values
        if time_index == 0:
            self.T_WGO_pre = self.parameter("initial_water_temp").value
            self.T_WGI_pre = self.parameter("initial_water_temp").value
            self.T_WCI_pre = self.parameter("initial_water_temp").value
            self.T_WCO_pre = self.parameter("initial_water_temp").value
            self.mode = 0 # Standby
        else:
            self.T_WGO_pre = self.variable("T_generators_out").values[time_index-1]
            self.T_WGI_pre = self.variable("T_generators_in").values[time_index-1]
            self.T_WCI_pre = self.variable("T_supply").values[time_index-1]
            self.T_WCO_pre = self.variable("T_return").values[time_index-1]
            self.mode = self.variable("mode").values[time_index-1]
        # Water mass flow: the generators available, in parallel, each at its flow
        self.generator_flows = [g.nominal_water_flow() if g.on_off else 0 for g in self.generators]
        self.design_water_flow = sum(self.generator_flows)
        self.Q_generators = [0] * len(self.generators)
        self.water_flow = self.design_water_flow
        self.T_WCI = self.T_WCI_pre
        self.T_WCO = self.T_WCO_pre
        self.T_WGI = self.T_WGI_pre
        self.T_WGO = self.T_WGO_pre

        # variables dictonary
        self.var_dic = self.get_parameter_variable_dictionary(time_index)

        # setpoints
        self.T_heat_sp = self.parameter("heating_water_setpoint").evaluate(self.var_dic)
        self.variable("heating_water_setpoint").values[time_index] = self.T_heat_sp
        self.T_cool_sp = self.parameter("cooling_water_setpoint").evaluate(self.var_dic)
        self.variable("cooling_water_setpoint").values[time_index] = self.T_cool_sp

        # on/off
        self.on_off = self.parameter("system_on_off").evaluate(self.var_dic)
        self.variable("on_off").values[time_index] = self.on_off

        # Q_coils load
        self.Q_coils = 0
        self.Q_coils_used = 0  # the one of the last iteration, the value stored
        self.coils_flow = 0
        self.coils_flow_used = 0

        # Pump defined
        if self.pump is None: # Pump defined
            self.Q_pump = 0

        # Water flow and volume properties
        if self.on_off:
            self.water_flow = self.design_water_flow
        else:
            self.water_flow = 0
        self.water_volume = self.parameter("total_water_volume").value

        # Iterative 
        if self.has_header:
            # the water of the loop is lumped at the supply to the secondary
            self.secondary_flow = self.secondary_design_flow if self.on_off else 0
            self.water_flow = self.secondary_flow
            self.running = list(self.running_pre)
            self.Q_pump = 0
            self.Q_pump_secondary = 0
            self.Q_gen = 0
            self.f_load = 0
            self.itera_T = Iterative_process(self.T_WCI_pre,tol=self.parameter("convergence_DT").value,n_ini_relax=3,rel_vel=0.8)
        else:
            self.itera_T = Iterative_process(self.T_WGO_pre,tol=self.parameter("convergence_DT").value,n_ini_relax=3,rel_vel=0.8)
        self.pre_iter = True

        # Control mode
        if self.parameter("system_control").value == "SCHEDULE_CONTROL":
            self.mode = self.parameter("system_mode").evaluate(self.var_dic)
           
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

    def can_heat(self):
        """True if the coils can take heat from the plant: it is on and, with
        SCHEDULE_CONTROL, not in cooling mode (its loads would be discarded)."""
        if not self.on_off:
            return False
        return not (self.parameter("system_control").value == "SCHEDULE_CONTROL" and self.mode == -1)

    def can_cool(self):
        """True if the coils can take cold from the plant: it is on and, with
        SCHEDULE_CONTROL, not in heating mode (its loads would be discarded)."""
        if not self.on_off:
            return False
        return not (self.parameter("system_control").value == "SCHEDULE_CONTROL" and self.mode == 1)

    def add_coil_load(self, Q_coil, water_flow=0):
        """Add the load of a coil in this iteration.

        Args:
            Q_coil (float): heat the coil gives to the water (W), positive when it heats
                the water (cooling coil), negative when it cools it (heating coil).
            water_flow (float, optional): water flow through the coil (dm³/s).
        """
        self.Q_coils += Q_coil
        self.coils_flow += water_flow
    
    def _update_expressions(self):
        self.T_avg = (self.T_WGO + self.T_WGI + self.T_WCI + self.T_WCO) / 4
        self.rho_cp = self.props["RHOCP_W"](self.T_avg) /1000  # Unit W/dm³K
        self.var_dic["T_w"] = self.T_avg
        self.var_dic["m_w"] = self.water_flow
        self.Q_loss = self.parameter("Q_loss").evaluate(self.var_dic)
        self.Q_process = self.parameter("Q_process").evaluate(self.var_dic)


    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)
        self.pre_iter = False
        self._update_expressions()
        if self.has_header:
            return self._iteration_header()
        self._check_mode()
        if self.water_flow == 0:
            self.T_WGO = self.T_WGO_pre + self.Q_loss*self.delta_t/(self.rho_cp * self.water_volume)    
            self.Q_gen = 0
        else:
            if self.mode == 0: # standby
                Q = self.Q_coils + self.Q_process + self.Q_loss + self.Q_pump
                self.T_WGO = self.T_WGO_pre + Q*self.delta_t/(self.rho_cp * self.water_volume)
                self.Q_gen = 0
            else: # Heating or cooling
                self._simulate_generator()            
        
        # Resto de temperaturas
        self.T_WGO = self.itera_T.estimate_next_x(self.T_WGO)     
        if self.water_flow == 0: 
            deltaT = self.T_WGO - self.T_WGO_pre
            self.T_WGI = self.T_WGI_pre + deltaT
            self.T_WCI = self.T_WCI_pre + deltaT
            self.T_WCO = self.T_WCO_pre + deltaT
        else:          
            self.T_WCI = self.T_WGO + (self.Q_loss/2)/(self.rho_cp * self.water_flow)
            self.T_WCO = self.T_WCI + (self.Q_coils + self.Q_process)/(self.rho_cp * self.water_flow)
            self.T_WGI = self.T_WCO + (self.Q_loss/2+self.Q_pump)/(self.rho_cp * self.water_flow)

        # The coils add their load again in the next iteration: keep the one
        # of this iteration to store it, then start again from 0
        self.Q_coils_used = self.Q_coils
        self.Q_coils = 0
        self.coils_flow_used = self.coils_flow
        self.coils_flow = 0
        # Test convergence
        return self.itera_T.converged() 

    def _check_mode(self):
        if self.on_off:
            if self.parameter("system_control").value == "LOAD_CONTROL":
                if self.Q_coils + self.Q_process < 0:
                    self.mode = 1 
                elif self.Q_coils + self.Q_process > 0:
                    self.mode = -1
                else:
                    self.mode = 0
            elif self.parameter("system_control").value == "SCHEDULE_CONTROL":
                if self.mode == 1: # Heating
                    self.Q_process = min(self.Q_process, 0)
                    self.Q_coils = min(self.Q_coils, 0)
                elif self.mode == -1: # Cooling
                    self.Q_process = max(self.Q_process, 0)
                    self.Q_coils = max(self.Q_coils, 0)
            if self.parameter("pump_operation").value == "ALLWAYS_ON":
                if self.pump is not None:
                    self.Q_pump = self._pumps_heat()
            elif self.parameter("pump_operation").value == "ON_LOAD":
                if self.Q_process + self.Q_coils != 0:
                    self.water_flow = self.design_water_flow
                    if self.pump is not None:
                        self.Q_pump = self._pumps_heat()
                    else:
                        self.Q_pump = 0
                else:
                    self.water_flow = 0        

    def _pumps_heat(self):
        if self.water_flow == 0:
            return 0
        return sum(g.get_pump_heat(f) for g, f in zip(self.generators, self.generator_flows))

    def _generators_load(self, mode, Q_required, T_wo=None, T_wi=None, flows=None):
        """Share a required load (positive) among the generators able to give it.

        Args:
            mode (int): 1 heating, -1 cooling.
            Q_required (float): load required (W, positive).
            T_wo (float, optional): outlet water temperature, T_WGO by default.
            T_wi (float, optional): inlet water temperature, T_WGI by default.
            flows (list, optional): water flow of each generator, generator_flows by default.

        Returns:
            tuple: (Q, F_load), load given (positive) and part load of the generators.
        """
        self.Q_generators = [0] * len(self.generators)
        args = (self.T_WGO if T_wo is None else T_wo, self.T_WGI if T_wi is None else T_wi)
        flows = self.generator_flows if flows is None else flows
        if len(self.generators) == 1:
            g = self.generators[0]
            if mode == 1:
                Q, f_load = g.get_heating_load(*args, flows[0], Q_required)
            else:
                Q, f_load = g.get_cooling_load(*args, flows[0], Q_required)
            self.Q_generators[0] = mode * Q
            return (Q, f_load)
        capacities = [g.get_capacity(mode, *args, f) for g, f in zip(self.generators, flows)]
        total = sum(capacities)
        if total <= 0 or Q_required <= 0:
            return (0, 0)
        if self.sequencing == "EQUAL_LOAD":
            F = min(Q_required / total, 1)
            for i, capacity in enumerate(capacities):
                self.Q_generators[i] = mode * F * capacity
        else:  # PRIORITY
            rest = Q_required
            for i, capacity in enumerate(capacities):
                q = min(rest, capacity)
                self.Q_generators[i] = mode * q
                rest -= q
        Q = sum(abs(q) for q in self.Q_generators)
        return (Q, Q / total)

    # _________________ Plant with a header (primary / secondary) _________________

    def _iteration_header(self):
        """One iteration of a plant with a header (secondary pumps).

        The water of the loop is lumped at the supply to the secondary, T_S (T_WCI).
        The secondary pumps move secondary_flow through the coils, the primary pump of
        each generator its nominal flow while it runs. The header is an ideal
        decoupler: if the primary flow is larger, the rest goes back to the generators
        through the bypass and mixes with the return; if smaller, part of the return
        goes to the supply. Each generator tries to give the setpoint at its outlet.
        """
        Q_sec = self._check_mode_header()
        m_s = self.secondary_flow
        cpV_dt = self.rho_cp * self.water_volume / self.delta_t
        nominal = [g.nominal_water_flow() if g.on_off else 0 for g in self.generators]
        self.Q_generators = [0] * len(self.generators)
        self.Q_gen = 0
        self.f_load = 0
        if not self.on_off or self.mode == 0:
            self.running = [False] * len(self.generators)
            self.Q_pump = self.Q_pump_secondary
            Q = (Q_sec + self.Q_pump) if self.on_off else self.Q_loss
            T_S = self.T_WCI_pre + Q / cpV_dt
        else:
            setpoint = self.T_heat_sp if self.mode == 1 else self.T_cool_sp
            # primary flow of the generators running (in the previous iteration)
            flows = [f if r else 0 for f, r in zip(nominal, self.running)]
            m_p = sum(flows)
            q = Q_sec / (self.rho_cp * m_s) if m_s > 0 else 0  # T_R - T_S
            # supply that gives the setpoint at the outlet of the generators
            T_S_target = setpoint + (m_s - m_p) / m_p * q if 0 < m_p < m_s else setpoint
            T_R = T_S_target + q
            T_pi = (m_s * T_R + (m_p - m_s) * setpoint) / m_p if m_p > m_s else T_R
            self.Q_pump = self.Q_pump_secondary + sum(
                g.get_pump_heat(f) for g, f in zip(self.generators, flows)
            )
            Q_required = cpV_dt * (T_S_target - self.T_WCI_pre) - (Q_sec + self.Q_pump)
            if self.mode * Q_required > 0:
                # every generator able to run is considered, at its nominal flow
                Q, self.f_load = self._generators_load(
                    self.mode, self.mode * Q_required, setpoint, T_pi, nominal
                )
                self.Q_gen = self.mode * Q
            self.running = [q_g != 0 for q_g in self.Q_generators]
            flows = [f if r else 0 for f, r in zip(nominal, self.running)]
            self.Q_pump = self.Q_pump_secondary + sum(
                g.get_pump_heat(f) for g, f in zip(self.generators, flows)
            )
            T_S = self.T_WCI_pre + (self.Q_gen + Q_sec + self.Q_pump) / cpV_dt
        self.T_S = self.itera_T.estimate_next_x(T_S)
        self._header_temperatures(Q_sec, nominal)
        self._end_iteration_()
        return self.itera_T.converged()

    def _check_mode_header(self):
        """Mode and secondary flow of a plant with a header.

        Returns:
            float: heat of the secondary to the water (W): coils, process and losses (the
                heat of the pumps is in Q_pump).
        """
        Q_coils = self.Q_coils
        if self.on_off:
            if self.parameter("system_control").value == "LOAD_CONTROL":
                total = Q_coils + self.Q_process
                self.mode = 1 if total < 0 else (-1 if total > 0 else 0)
            elif self.mode == 1:
                self.Q_process = min(self.Q_process, 0)
                Q_coils = min(Q_coils, 0)
            elif self.mode == -1:
                self.Q_process = max(self.Q_process, 0)
                Q_coils = max(Q_coils, 0)
            if self.parameter("pump_operation").value == "ON_LOAD" and self.Q_process + Q_coils == 0:
                self.secondary_flow = 0
            else:
                self.secondary_flow = self.secondary_design_flow
        else:
            self.secondary_flow = 0
        self.Q_coils = Q_coils
        self.water_flow = self.secondary_flow
        self.Q_pump_secondary = sum(
            p.get_heat_gain(p.parameter("nominal_water_flow").value) for p in self.secondary_pumps
        ) if self.secondary_flow > 0 else 0
        return self.Q_coils + self.Q_process + self.Q_loss

    def _header_temperatures(self, Q_sec, nominal):
        """Temperatures of the secondary and of the generators from T_S and the flows."""
        m_s = self.secondary_flow
        flows = [f if r else 0 for f, r in zip(nominal, self.running)]
        m_p = sum(flows)
        self.generator_flows = flows
        self.primary_flow = m_p
        self.T_WCI = self.T_S
        self.T_WCO = self.T_S + Q_sec / (self.rho_cp * m_s) if m_s > 0 else self.T_S
        if m_p == 0:
            self.T_WGI = self.T_WGO = self.T_WCO if m_s > 0 else self.T_S
            return
        if m_p >= m_s:  # the generators give the supply; the rest goes back
            T_po = self.T_S
            self.T_WGI = (m_s * self.T_WCO + (m_p - m_s) * T_po) / m_p if m_s > 0 else T_po
        else:  # part of the return goes to the supply
            T_po = (m_s * self.T_S - (m_s - m_p) * self.T_WCO) / m_p
            self.T_WGI = self.T_WCO
        self.T_WGO = T_po

    def _end_iteration_(self):
        # The coils add their load again in the next iteration: keep the one
        # of this iteration to store it, then start again from 0
        self.Q_coils_used = self.Q_coils
        self.Q_coils = 0
        self.coils_flow_used = self.coils_flow
        self.coils_flow = 0

    def _simulate_generator(self): # Heating or cooling mode
        Q = self.Q_coils + self.Q_process + self.Q_loss + self.Q_pump
        T_WGO_FF = Q*self.delta_t/(self.rho_cp * self.water_volume)+self.T_WGO_pre

        if self.mode == 1: # Heating
            if T_WGO_FF > self.T_heat_sp: # no Q required, generator off
                self.Q_gen = 0
                self.Q_generators = [0] * len(self.generators)
                self.T_WGO = T_WGO_FF
            else: # Q required, generator on
                self.T_WGO = self.T_heat_sp
                Q_required = -Q + self.rho_cp * self.water_volume * (self.T_WGO - self.T_WGO_pre)/self.delta_t
                self.Q_gen, self.f_load = self._generators_load(1, Q_required)
                if self.f_load == 1 or self.f_load == 0: # Not enough heating power, update T_WGO with the actual Q_gen
                    delta_T = (self.Q_gen+self.Q_pump+self.Q_coils+self.Q_process+self.Q_loss)*self.delta_t/(self.rho_cp * self.water_volume)
                    self.T_WGO = self.T_WGO_pre + delta_T
        elif self.mode == -1: #Cooling
            if T_WGO_FF < self.T_cool_sp: # no Q required, generator off
                self.Q_gen = 0
                self.Q_generators = [0] * len(self.generators)
                self.T_WGO = T_WGO_FF
            else: # Q required, generator on
                self.T_WGO = self.T_cool_sp
                Q_required = -Q + self.rho_cp * self.water_volume * (self.T_WGO - self.T_WGO_pre)/self.delta_t
                self.Q_gen, self.f_load = self._generators_load(-1, -Q_required)
                self.Q_gen = -self.Q_gen
                if self.f_load == 1 or self.f_load == 0: # Not enough cooling power, update T_WGO with the actual Q_gen
                    delta_T = (self.Q_gen+self.Q_pump+self.Q_coils+self.Q_process+self.Q_loss)*self.delta_t/(self.rho_cp * self.water_volume)
                    self.T_WGO = self.T_WGO_pre + delta_T

    def limit_water_temperature(self, T):
        if T > self.max_water_temp:
            return self.max_water_temp
        elif T < self.min_water_temp:
            return self.min_water_temp
        else:   
            return T

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        if self.has_header:
            self._post_iteration_header(time_index)
            return
        self.variable("primary_flow").values[time_index] = self.water_flow
        self.variable("secondary_flow").values[time_index] = self.water_flow
        self.variable("mode").values[time_index] = self.mode
        self.variable("T_generators_out").values[time_index] = self.limit_water_temperature(self.T_WGO)
        self.variable("T_generators_in").values[time_index] = self.limit_water_temperature(self.T_WGI)
        self.variable("T_return").values[time_index] = self.limit_water_temperature(self.T_WCO)
        self.variable("T_supply").values[time_index] = self.limit_water_temperature(self.T_WCI)
        self.variable("T_mean").values[time_index] = self.limit_water_temperature(self.T_avg)
        self.variable("coils_flow").values[time_index] = self.coils_flow_used
        if self.water_flow == 0:
            self.variable("Q_generators").values[time_index] = 0
            self.variable("Q_coils").values[time_index] = 0
            self.variable("Q_process").values[time_index] = 0
            self.variable("Q_pump").values[time_index] = 0
            self.variable("pumps_power").values[time_index] = 0
            self.variable("generators_power").values[time_index] = 0
            self.variable("generators_fuel_power").values[time_index] = 0
            self.variable("electric_power").values[time_index] = 0
            for g in self.generators:
                g.set_operation(time_index, 0, self.T_WGO, self.T_WGI, 0, self.sequencing)
        else:
            running = self.mode in (1, -1)
            power = fuel = pump_power = 0
            for g, Q_g, flow in zip(self.generators, self.Q_generators, self.generator_flows):
                p, f, _ = g.set_operation(
                    time_index, Q_g if running else 0, self.T_WGO, self.T_WGI, flow, self.sequencing
                )
                power += p
                fuel += f
                pump_power += g.get_pump_power(flow)
            self.variable("Q_generators").values[time_index] = self.Q_gen
            self.variable("Q_coils").values[time_index] = self.Q_coils_used
            self.variable("Q_process").values[time_index] = self.Q_process
            self.variable("Q_pump").values[time_index] = self.Q_pump
            self.variable("pumps_power").values[time_index] = pump_power
            self.variable("generators_power").values[time_index] = power
            self.variable("generators_fuel_power").values[time_index] = fuel
            self.variable("electric_power").values[time_index] = power + pump_power
        self.variable("Q_loss").values[time_index] = self.Q_loss
        self.variable("delta_U").values[time_index] = self.rho_cp * self.water_volume * (self.T_WGO - self.T_WGO_pre)/self.delta_t

    def _post_iteration_header(self, time_index):
        m_s = self.secondary_flow
        m_p = self.primary_flow
        running = self.on_off and self.mode in (1, -1)
        self.variable("mode").values[time_index] = self.mode
        for key, T in (("T_generators_out", self.T_WGO), ("T_generators_in", self.T_WGI),
                       ("T_return", self.T_WCO), ("T_supply", self.T_WCI), ("T_mean", self.T_avg)):
            self.variable(key).values[time_index] = self.limit_water_temperature(T)
        self.variable("primary_flow").values[time_index] = m_p
        self.variable("secondary_flow").values[time_index] = m_s
        self.variable("bypass_flow").values[time_index] = m_p - m_s
        self.variable("coils_flow").values[time_index] = self.coils_flow_used
        power = fuel = pump_power = 0
        for g, Q_g, flow in zip(self.generators, self.Q_generators, self.generator_flows):
            Q_g = Q_g if running and flow > 0 else 0
            T_wo = self.T_WGI + Q_g / (self.rho_cp * flow) if flow > 0 else self.T_WGI
            p, f, _ = g.set_operation(time_index, Q_g, T_wo, self.T_WGI, flow, self.sequencing)
            power += p
            fuel += f
            pump_power += g.get_pump_power(flow)
        secondary_pump_power = sum(
            p.get_power(p.parameter("nominal_water_flow").value) for p in self.secondary_pumps
        ) if m_s > 0 else 0
        Q_gen = self.Q_gen if running else 0
        self.variable("Q_generators").values[time_index] = Q_gen
        self.variable("Q_coils").values[time_index] = self.Q_coils_used if m_s > 0 else 0
        self.variable("Q_process").values[time_index] = self.Q_process if m_s > 0 else 0
        self.variable("Q_pump").values[time_index] = self.Q_pump if self.on_off else 0
        self.variable("pumps_power").values[time_index] = pump_power + secondary_pump_power
        self.variable("secondary_pumps_power").values[time_index] = secondary_pump_power
        self.variable("generators_power").values[time_index] = power
        self.variable("generators_fuel_power").values[time_index] = fuel
        self.variable("electric_power").values[time_index] = power + pump_power + secondary_pump_power
        self.variable("Q_loss").values[time_index] = self.Q_loss
        self.variable("delta_U").values[time_index] = (
            self.rho_cp * self.water_volume * (self.T_S - self.T_WCI_pre) / self.delta_t
        )
        self.running_pre = list(self.running)
