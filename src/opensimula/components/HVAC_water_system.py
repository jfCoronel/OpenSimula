import numpy as np
from opensimula.Component import Component  # noqa: N999
from opensimula.Iterative_process import Iterative_process
from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_boolean,
    Parameter_component,
    Parameter_component_list,
    Parameter_float,
    Parameter_float_list,
    Parameter_math_exp,
    Parameter_options,
    Parameter_variable_list,
)
from opensimula.Variable import Variable
from opensimula.energy import mode_from_plant, split_dhw
from opensimula.components.Pump import staged_pump_flows


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
        # a storage tank: its water is the water of the plant, which then works as a
        # header (the tank decouples the generators from the loads)
        self.add_parameter(Parameter_component("tank", "not_defined", ["Water_tank"]))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("heating_water_setpoint", "45", "°C"))
        self.add_parameter(Parameter_math_exp("cooling_water_setpoint", "7", "°C"))
        self.add_parameter(Parameter_math_exp("system_on_off", "1", "on/off"))
        self.add_parameter(
            Parameter_options("pump_operation", "ALLWAYS_ON", ["ALLWAYS_ON", "ON_LOAD"]) # ALLWAYS_ON: pump on when system is on, ON_LOAD: pump on when heating or cooling load is required
        )
        # CONSTANT: the design flow while on (three-way valves); VARIABLE: the flow the
        # coils ask for (two-way valves), between minimum_flow and the design flow
        self.add_parameter(Parameter_options("flow_control", "CONSTANT", ["CONSTANT", "VARIABLE"]))
        # DHW first: the DHW demands and the DHW charging circuits get water at the heating
        # setpoint, up to the capacity of the generators; the other loads the rest
        self.add_parameter(Parameter_boolean("dhw_priority", False))
        self.add_parameter(Parameter_float("minimum_flow", 0, "frac", min=0, max=1))
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
        # loads of the coils (of air systems, directly or through circuits) and of DHW
        # demands: Q_loads = Q_heating_coils + Q_cooling_coils + Q_dhw
        self.add_variable(Variable("Q_loads", unit="W"))
        self.add_variable(Variable("Q_heating_coils", unit="W"))
        self.add_variable(Variable("Q_cooling_coils", unit="W"))
        self.add_variable(Variable("Q_dhw", unit="W"))
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
        series = [g for g in self.parameter("generators").component
                  if g is not None and g.parameter("connection").value == "SERIES"]
        if series and self.parameter("tank").value == "not_defined":
            msg = (f"{self.parameter('name').value}, generators in SERIES (at the outlet) need a "
                   "plant with a tank.")
            errors.append(Message(msg, "ERROR"))
        if any(g.parameter("equipment").component is not None
               and g.parameter("equipment").component.parameter("type").value == "Solar_collector"
               for g in series):
            msg = (f"{self.parameter('name').value}, a Solar_collector generator cannot be in "
                   "SERIES: it heats the tank (PARALLEL).")
            errors.append(Message(msg, "ERROR"))
        if (self.parameter("tank").value == "not_defined" and any(
                g is not None and g.parameter("equipment").component is not None
                and g.parameter("equipment").component.parameter("type").value == "Solar_collector"
                for g in self.parameter("generators").component)):
            msg = (f"{self.parameter('name').value}, a generator with a Solar_collector needs a "
                   "plant with a tank (the heat of the sun is stored in it).")
            errors.append(Message(msg, "ERROR"))
        if (self.parameter("flow_control").value == "VARIABLE"
                and self.parameter("minimum_flow").value == 0
                and str(self.parameter("Q_process").value).strip() not in ("0", "0.0", "")):
            msg = (f"{self.parameter('name').value}, with VARIABLE flow_control a Q_process "
                   "has no water flow of its own: set minimum_flow > 0 or it is not served "
                   "while no coil asks for water.")
            errors.append(Message(msg, "WARNING"))
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self.props = self._sim_.props # Fluid properties
        self.delta_t = delta_t
        self.file_met = self.project().parameter("simulation_file_met").component
        # Parameters
        self.generators = self.parameter("generators").component
        for g in self.generators:  # for the mode of their pumps in the energy report
            g.plant = self
        self.sequencing = self.parameter("sequencing").value
        self.variable_flow = self.parameter("flow_control").value == "VARIABLE"
        self.minimum_flow = self.parameter("minimum_flow").value
        # The loop is moved by the pumps of the generators (in parallel), that can be
        # not defined (Q_pump = 0)
        self.pump = next((g.get_pump() for g in self.generators if g.get_pump() is not None), None)
        self.design_water_flow = sum(g.nominal_water_flow() for g in self.generators)
        # Header: the secondary pumps move the water to the coils, the primary pumps of
        # the generators only that of the generators running
        self.secondary_pumps = self.parameter("pumps").component
        self.tank = (self.parameter("tank").component
                     if self.parameter("tank").value != "not_defined" else None)
        self.has_header = len(self.secondary_pumps) > 0 or self.tank is not None
        self.solar_generators = [i for i, g in enumerate(self.generators) if g.is_solar]
        # generators in series at the outlet, in the order of the list
        self.series_generators = [i for i, g in enumerate(self.generators) if g.is_series]
        self.dhw_priority = self.parameter("dhw_priority").value
        self.priority_capacity = self.priority_used = 0.0
        self.stratified = self.tank is not None and self.tank.n_nodes > 1
        self.backup_on_pre = False
        self.Q_solar = 0
        self._dhw_only = None
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
        self.nominal_flows = list(self.generator_flows)
        self.design_water_flow = sum(self.generator_flows)
        self.Q_generators = [0] * len(self.generators)
        self.water_flow = self.design_water_flow
        self.T_WCI = self.T_WCI_pre
        if self.tank is not None and time_index > 0:
            # the state is the water of the tank, not the supply: generators in series
            # heat the supply after it (the coils see that supply first)
            self.T_WCI_pre = self.tank.variable("temperature").values[time_index - 1]
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

        # loads (variable Q_loads), its part of DHW demands and of heating and cooling coils
        self.Q_coils = 0
        self.Q_coils_used = 0  # the one of the last iteration, the value stored
        self.Q_dhw = self.Q_dhw_used = 0
        self.Q_heat = self.Q_heat_used = self.Q_cool = self.Q_cool_used = 0
        self.coils_flow = 0
        self.coils_flow_used = 0
        # DHW priority: the capacity of the generators in parallel that heat, at the
        # setpoint, for the DHW loads of this time step
        self.priority_used = 0.0
        self.priority_capacity = 0.0
        if self.dhw_priority and self.on_off:
            self.priority_capacity = sum(
                g.get_capacity(1, self.T_heat_sp, self.T_WCO_pre, g.nominal_water_flow())
                for g in self.generators)

        # Pump defined
        if self.pump is None: # Pump defined
            self.Q_pump = 0

        # Water flow and volume properties
        if self.on_off:
            self.water_flow = self.design_water_flow
        else:
            self.water_flow = 0
        self.water_volume = (self.tank.get_volume() if self.tank is not None
                             else self.parameter("total_water_volume").value)
        self.Q_tank_loss = 0
        self.Q_series = 0.0  # heat of the generators in series, of the last iteration
        self.series_ops = {}
        # thermostat of a tank: heating in the previous time step without reaching the
        # setpoint goes on; otherwise it starts dead_band below the setpoint
        self.tank_charging_pre = (
            self.tank is not None and time_index > 0
            and self.variable("Q_generators").values[time_index - 1] > 0
            and self.variable("T_supply").values[time_index - 1] < self.T_heat_sp - 1e-6)

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
            if self.stratified:
                if self.tank.nodes is None or time_index == 0:
                    self.tank.nodes = np.full(self.tank.n_nodes, self.parameter("initial_water_temp").value)
                self.nodes_pre = np.array(self.tank.nodes)
                self.nodes = self.nodes_pre
                self.T_ret = self.T_WCI_pre
                self.T_backup_in = self.nodes_pre[self.tank.backup_node]
                self.backup_on = False
                self.rho_cp = self.props["RHOCP_W"](float(np.mean(self.nodes_pre))) / 1000
        else:
            self.itera_T = Iterative_process(self.T_WGO_pre,tol=self.parameter("convergence_DT").value,n_ini_relax=3,rel_vel=0.8)
        self.pre_iter = True

        # Control mode
        if self.parameter("system_control").value == "SCHEDULE_CONTROL":
            self.mode = self.parameter("system_mode").evaluate(self.var_dic)
           
    def get_cooling_coil_inlet_T(self): 
        if self.pre_iter and self.tank is None:  # a tank: the water it has
            return self.T_cool_sp
        else:
            return self.T_WCI

    def get_heating_coil_inlet_T(self):
        if self.pre_iter and self.tank is None:  # a tank: the water it has
            return self.T_heat_sp
        else:
            return self.T_WCI

    def dhw_supply_T(self):
        """Water temperature to the DHW loads (DHW demands, DHW charging circuits): with
        DHW priority the heating setpoint while the plant can heat (the generators work
        for them first), otherwise the supply of the plant."""
        if self.dhw_priority and self.can_heat():
            return self.T_heat_sp
        return self.get_heating_coil_inlet_T()

    def take_dhw_heat(self, Q):
        """Heat a DHW load takes with DHW priority (W, positive): at most what is left
        of the capacity of the generators in this iteration. Without priority, Q."""
        if not (self.dhw_priority and self.can_heat()):
            return Q
        allowed = max(0.0, min(Q, self.priority_capacity - self.priority_used))
        self.priority_used += allowed
        return allowed

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

    def add_coil_load(self, Q_coil, water_flow=0, dhw=0.0):
        """Add the load of a coil in this iteration.

        Args:
            Q_coil (float): heat the coil gives to the water (W), positive when it heats
                the water (cooling coil), negative when it cools it (heating coil).
            water_flow (float, optional): water flow through the coil (dm³/s).
            dhw (float, optional): the part of Q_coil that is domestic hot water (W, same
                sign): DHW demands and circuits feeding them.
        """
        self.Q_coils += Q_coil
        self.coils_flow += water_flow
        self.Q_dhw += dhw
        if Q_coil - dhw < 0:  # coils: heating ones take heat from the water
            self.Q_heat += Q_coil - dhw
        else:
            self.Q_cool += Q_coil - dhw
    
    def _update_expressions(self):
        self.T_avg = (self.T_WGO + self.T_WGI + self.T_WCI + self.T_WCO) / 4
        self.rho_cp = self.props["RHOCP_W"](self.T_avg) /1000  # Unit W/dm³K
        self.var_dic["T_w"] = self.T_avg
        self.var_dic["m_w"] = self.water_flow
        self.Q_loss = self.parameter("Q_loss").evaluate(self.var_dic)
        self.parameter_Q_loss = self.Q_loss
        if self.tank is not None and not self.stratified:  # losses of the tank
            # at the temperature of the tank (T_S), not of the supply after the generators
            # in series; T_S of the previous iteration (or time step)
            self.Q_tank_loss = -self.tank.get_loss(getattr(self, "T_S", self.T_WCI_pre))
            self.Q_loss += self.Q_tank_loss
        self.Q_process = self.parameter("Q_process").evaluate(self.var_dic)


    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)
        self.pre_iter = False
        self._update_expressions()
        if self.stratified:
            return self._iteration_stratified()
        if self.has_header:
            return self._iteration_header()
        self._check_mode()
        if self.variable_flow:
            self._variable_flow()
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
        self.Q_dhw_used = self.Q_dhw
        self.Q_dhw = 0
        self.Q_heat_used, self.Q_heat = self.Q_heat, 0
        self.Q_cool_used, self.Q_cool = self.Q_cool, 0
        self.coils_flow_used = self.coils_flow
        self.coils_flow = 0
        self.priority_used = 0.0
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

    def _variable_flow(self):
        """Loop flow of a plant without header with VARIABLE flow_control: the flow the
        coils ask for, between the minimum and the design flow, shared by the generators
        in proportion to their nominal flow (their pumps move it)."""
        design = self.design_water_flow
        if not self.on_off or design <= 0:
            flow = 0
        else:
            flow = min(max(self.coils_flow, self.minimum_flow * design), design)
        self.water_flow = flow
        self.generator_flows = [f * flow / design if design > 0 else 0 for f in self.nominal_flows]
        self.Q_pump = self._pumps_heat()

    def _secondary_pump_flows(self):
        """Flow of each secondary pump: all at their nominal flow with CONSTANT
        flow_control, staged with VARIABLE."""
        if self.secondary_flow <= 0:
            return [0] * len(self.secondary_pumps)
        if self.variable_flow:
            return staged_pump_flows(self.secondary_pumps, self.secondary_flow)
        return [p.parameter("nominal_water_flow").value for p in self.secondary_pumps]

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

    # _________________ Plant with a stratified tank _________________

    def _iteration_stratified(self):
        """One iteration of a plant with a stratified tank (Water_tank with nodes).

        From the temperatures of the nodes at the start of the time step: the water the
        loads draw leaves at the top and comes back at the bottom (at the temperature
        that gives their load), the nodes lose heat, the solar collectors heat the bottom
        node with the water of that node, and the other generators heat the node of the
        backup heater, where the thermostat is, up to the setpoint (as much as their
        capacity gives). Heated water rises. The supply to the loads is the mean
        temperature of the water leaving at the top.
        """
        tank = self.tank
        dt = self.delta_t
        T0 = self.nodes_pre
        rho_cp = self.props["RHOCP_W"](float(np.mean(T0))) / 1000  # W/(dm³·K)
        self.rho_cp = rho_cp
        heating = self.on_off and self.can_heat()
        self.mode = 1 if heating else 0
        Q_series_pre = self.Q_series
        Q_coils = (self.Q_coils + Q_series_pre) if heating else 0  # the tank gives the rest
        m = self.coils_flow if heating else 0
        # draw: two passes, the second with the return temperature that gives the load
        T, T_out = tank.advect(T0, m, T0[-1], dt)
        if m > 0:
            T_ret = T_out + Q_coils / (rho_cp * m)
            T, T_out = tank.advect(T0, m, T_ret, dt)
        else:
            T_ret = T_out
        self.T_ret = T_ret
        # losses of the tank and Q_loss of the plant (shared by the nodes)
        T, lost = tank.losses(T, rho_cp, dt)
        self.Q_tank_loss = -lost
        T = T + self.parameter_loss_per_node(rho_cp)
        # solar collectors, on the bottom node, at most up to their maximum temperature
        solar = [0.0] * len(self.generators)
        if heating:
            for i in self.solar_generators:
                solar[i] = self.generators[i].get_solar_heat(T0[tank.solar_node])
        Q_solar = sum(solar)
        if Q_solar > 0:
            T_max = min(self.generators[i].equipment.parameter("max_temperature").value
                        for i in self.solar_generators)
            def too_hot(Q):
                return tank.add_heat(T, tank.solar_node, Q, rho_cp, dt).max() > T_max
            if too_hot(Q_solar):
                low, high = 0.0, Q_solar
                for _ in range(50):
                    mid = (low + high) / 2
                    low, high = (low, mid) if too_hot(mid) else (mid, high)
                solar = [s * low / Q_solar for s in solar]
                Q_solar = low
            T = tank.add_heat(T, tank.solar_node, Q_solar, rho_cp, dt)
        # backup on its node: thermostat with dead band, up to the setpoint
        j = tank.backup_node
        nominal = [g.nominal_water_flow() if g.on_off else 0 for g in self.generators]
        self.Q_generators = [0.0] * len(self.generators)
        Q_backup = 0.0
        self.f_load = 0
        sp = self.T_heat_sp
        start = self.backup_on_pre or T[j] < sp - tank.get_dead_band()
        if heating and start and T[j] < sp:
            low, high = 0.0, rho_cp * tank.get_volume() * (sp - T[j]) / dt
            for _ in range(60):  # the heat that leaves the node of the heater at sp
                mid = (low + high) / 2
                if tank.add_heat(T, j, mid, rho_cp, dt)[j] < sp:
                    low = mid
                else:
                    high = mid
            Q_backup, self.f_load = self._generators_load(1, high, sp, T[j], nominal)
            T = tank.add_heat(T, j, Q_backup, rho_cp, dt)
        self.backup_on = Q_backup > 0 and T[j] < sp - 1e-6
        self.Q_generators = [q + s for q, s in zip(self.Q_generators, solar)]
        self.Q_solar = Q_solar
        self.Q_gen = Q_backup + Q_solar
        self.running = [q != 0 for q in self.Q_generators]
        self.generator_flows = [f if r else 0 for f, r in zip(nominal, self.running)]
        self.Q_pump = 0  # the heat of the pumps is not counted in a stratified tank
        self.nodes = T
        self.T_backup_in = T0[j]
        self.water_flow = self.secondary_flow = m
        self.T_S = self.itera_T.estimate_next_x(T_out if m > 0 else T[0])
        self.T_WCI = self.T_S
        self._series(self.T_S, m if heating else 0)
        self._end_iteration_()
        return self.itera_T.converged() and self._series_converged(Q_series_pre)

    def parameter_loss_per_node(self, rho_cp):
        """Temperature change of each node by the Q_loss expression of the plant."""
        return self.parameter_Q_loss * self.delta_t / (rho_cp * self.tank.get_volume())

    def _post_iteration_stratified(self, time_index):
        T = self.nodes
        rho_cp = self.rho_cp
        self.variable("mode").values[time_index] = self.mode
        self.variable("T_supply").values[time_index] = self.T_WCI
        self.variable("T_return").values[time_index] = self.T_ret
        self.variable("T_mean").values[time_index] = float(np.mean(T))
        self.variable("T_generators_in").values[time_index] = self.T_backup_in
        self.variable("primary_flow").values[time_index] = sum(self.generator_flows)
        self.variable("secondary_flow").values[time_index] = self.secondary_flow
        self.variable("coils_flow").values[time_index] = self.coils_flow_used
        power = fuel = pump_power = 0
        T_out = self.T_backup_in
        for i, (g, Q_g, flow) in enumerate(zip(self.generators, self.Q_generators, self.generator_flows)):
            T_wi = self.nodes_pre[self.tank.solar_node] if g.is_solar else self.T_backup_in
            T_wo = T_wi + Q_g / (rho_cp * flow) if flow > 0 else T_wi
            if i in self.series_ops:
                Q_g, T_wi, T_wo, flow = self.series_ops[i]
            elif not g.is_solar and Q_g > 0:
                T_out = T_wo
            p, f, _ = g.set_operation(time_index, Q_g, T_wo, T_wi, flow, self.sequencing)
            power += p
            fuel += f
            pump_power += g.get_pump_power(flow)
        self.variable("T_generators_out").values[time_index] = T_out
        self.variable("Q_generators").values[time_index] = self.Q_gen
        self.variable("Q_loads").values[time_index] = self.Q_coils_used if self.mode == 1 else 0
        self.variable("Q_dhw").values[time_index] = self.Q_dhw_used if self.mode == 1 else 0
        self._store_coils(time_index, self.mode == 1)
        self.variable("Q_process").values[time_index] = 0
        self.variable("Q_pump").values[time_index] = 0
        self.variable("Q_loss").values[time_index] = self.Q_tank_loss + self.parameter_Q_loss
        self.variable("pumps_power").values[time_index] = pump_power
        self.variable("secondary_pumps_power").values[time_index] = 0
        self.variable("generators_power").values[time_index] = power
        self.variable("generators_fuel_power").values[time_index] = fuel
        self.variable("electric_power").values[time_index] = power + pump_power
        self.variable("delta_U").values[time_index] = float(
            np.sum(rho_cp * self.tank.node_volume() * (T - self.nodes_pre)) / self.delta_t)
        self.tank.set_state(time_index, float(np.mean(T)), T, loss=-self.Q_tank_loss)
        self.backup_on_pre = self.backup_on

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
        # the generators in series give part of the load of the coils: the tank gives
        # the rest (their heat of the previous iteration)
        Q_series_pre = self.Q_series
        Q_sec = Q_sec + Q_series_pre
        m_s = self.secondary_flow
        cpV_dt = self.rho_cp * self.water_volume / self.delta_t
        nominal = [g.nominal_water_flow() if g.on_off else 0 for g in self.generators]
        solar = self._solar_heat(cpV_dt, Q_sec)  # of each generator, always taken
        Q_solar = sum(solar)
        self.Q_generators = [0] * len(self.generators)
        self.Q_gen = 0
        self.f_load = 0
        if not self.on_off or self.mode == 0:
            self.running = [s > 0 for s in solar]
            self.Q_pump = self.Q_pump_secondary + self._running_pumps_heat(nominal)
            Q = (Q_sec + self.Q_pump + Q_solar) if self.on_off else self.Q_loss
            T_S = self.T_WCI_pre + Q / cpV_dt
        else:
            setpoint = self.T_heat_sp if self.mode == 1 else self.T_cool_sp
            # primary flow of the generators running (in the previous iteration)
            flows = [f if r else 0 for f, r in zip(nominal, self.running)]
            m_p = sum(flows)
            # T_R - T_S (the losses of a tank are not in the return)
            q = (Q_sec - self.Q_tank_loss) / (self.rho_cp * m_s) if m_s > 0 else 0
            # supply that gives the setpoint at the outlet of the generators
            T_S_target = setpoint + (m_s - m_p) / m_p * q if 0 < m_p < m_s else setpoint
            T_R = T_S_target + q
            T_pi = (m_s * T_R + (m_p - m_s) * setpoint) / m_p if m_p > m_s else T_R
            self.Q_pump = self.Q_pump_secondary + sum(
                g.get_pump_heat(f) for g, f in zip(self.generators, flows)
            )
            Q_required = cpV_dt * (T_S_target - self.T_WCI_pre) - (Q_sec + self.Q_pump + Q_solar)
            if self.mode * Q_required > 0 and self._tank_thermostat(cpV_dt, Q_sec + Q_solar):
                # every generator able to run is considered, at its nominal flow
                Q, self.f_load = self._generators_load(
                    self.mode, self.mode * Q_required, setpoint, T_pi, nominal
                )
                self.Q_gen = self.mode * Q
                if self.f_load >= 1:  # at full capacity: at the actual temperatures
                    self._header_at_capacity(Q_sec + Q_solar, cpV_dt, nominal, m_s, setpoint, q)
            self.running = [q_g != 0 or s > 0 for q_g, s in zip(self.Q_generators, solar)]
            self.Q_pump = self.Q_pump_secondary + self._running_pumps_heat(nominal)
            T_S = self.T_WCI_pre + (self.Q_gen + Q_solar + Q_sec + self.Q_pump) / cpV_dt
        # the solar generators in the shares and the total of the generators
        if Q_solar > 0:
            self.Q_generators = [q_g + s for q_g, s in zip(self.Q_generators, solar)]
            self.Q_gen += Q_solar
        self.Q_solar = Q_solar
        self.T_S = self.itera_T.estimate_next_x(T_S)
        self._header_temperatures(Q_sec, nominal)
        self._series(self.T_S, m_s)
        self._end_iteration_()
        return self.itera_T.converged() and self._series_converged(Q_series_pre)

    def _series(self, T_in, flow):
        """The generators in series at the outlet: the water leaving the plant at T_in
        with flow goes through them in the order of the list; each heats it towards
        the heating setpoint as far as its capacity allows. Sets the supply to the
        loads (T_WCI), their heat (Q_series, in Q_generators and Q_gen) and
        series_ops {index: (Q, T_in, T_out, flow)} for the post iteration."""
        self.series_ops = {}
        Q_total = 0.0
        T = T_in
        if self.series_generators and flow > 0 and self.on_off and self.mode == 1:
            for i in self.series_generators:
                g = self.generators[i]
                Q = g.get_series_heat(T, self.T_heat_sp, flow, self.rho_cp)
                T_out = T + Q / (self.rho_cp * flow)
                self.series_ops[i] = (Q, T, T_out, flow)
                self.Q_generators[i] = Q
                Q_total += Q
                T = T_out
        self.Q_series = Q_total
        self.Q_gen += Q_total
        self.T_WCI = T
        if self.series_ops:
            self.generator_flows = [flow if i in self.series_ops else f
                                    for i, f in enumerate(self.generator_flows)]

    def _series_converged(self, Q_series_pre):
        return abs(self.Q_series - Q_series_pre) <= max(1e-3 * abs(self.Q_series), 0.01)

    def _running_pumps_heat(self, nominal):
        """Heat of the primary pumps of the generators running."""
        return sum(g.get_pump_heat(f if r else 0)
                   for g, f, r in zip(self.generators, nominal, self.running))

    def _solar_heat(self, C, Q_sec):
        """Heat of the solar collector generators (W, each), with the water of the tank
        entering them: all of it is taken, unless the tank would go above the maximum
        temperature of the collectors (then less, as if they stopped part of the time)."""
        solar = [0.0] * len(self.generators)
        if not self.solar_generators or not self.on_off or self.mode == -1:
            return solar
        for i in self.solar_generators:
            solar[i] = self.generators[i].get_solar_heat(self.T_WCI_pre)
        total = sum(solar)
        if total > 0:
            T_max = min(self.generators[i].equipment.parameter("max_temperature").value
                        for i in self.solar_generators)
            pumps = sum(self.generators[i].get_pump_heat(self.generators[i].nominal_water_flow())
                        for i in self.solar_generators if solar[i] > 0)
            room = C * (T_max - self.T_WCI_pre) - (Q_sec + self.Q_pump_secondary + pumps)
            if total > room:
                solar = [s * max(room, 0) / total for s in solar]
        return solar

    def _tank_thermostat(self, C, Q_sec):
        """False if the thermostat of the tank keeps the generators off: in heating, not
        heating in the previous time step and the water, without them, not below the
        setpoint minus the dead band."""
        if self.tank is None or self.mode != 1 or self.tank_charging_pre:
            return True
        T_free = self.T_WCI_pre + (Q_sec + self.Q_pump_secondary) / C
        return T_free < self.T_heat_sp - self.tank.get_dead_band()

    def _header_at_capacity(self, Q_sec, C, nominal, m_s, setpoint, q):
        """The generators cannot give the setpoint: they give their full capacity at the
        actual outlet and inlet temperatures, which follow from the supply T_S through
        the mixing in the header. T_S = T_S_pre + (capacity(T_S) + rest) / C is found
        by bisection (nothing to find if the capacity does not depend on them)."""
        mode = self.mode
        flows = [f if r else 0 for f, r in zip(nominal, self.running)]
        rest = Q_sec + self.Q_pump

        def capacity(T_S):
            m_p = sum(nominal) if not any(self.running) else sum(flows)
            if m_p >= m_s or m_p == 0:
                T_po = T_S
                T_pi = (m_s * (T_S + q) + (m_p - m_s) * T_S) / m_p if m_p > 0 else T_S + q
            else:
                T_po = T_S - (m_s - m_p) / m_p * q
                T_pi = T_S + q
            return mode * self._generators_load(mode, float("inf"), T_po, T_pi, nominal)[0]

        T1 = self.T_WCI_pre + (self.Q_gen + rest) / C
        if capacity(T1) == self.Q_gen:  # independent of the temperatures (boilers)
            return
        def h(T):
            return T - self.T_WCI_pre - (capacity(T) + rest) / C

        T_free = self.T_WCI_pre + rest / C
        low, high = sorted((setpoint, T_free))
        h_low = h(low)
        for _ in range(60):
            mid = (low + high) / 2
            h_mid = h(mid)
            if (h_mid > 0) == (h_low > 0):
                low, h_low = mid, h_mid
            else:
                high = mid
            if high - low < 1e-7:
                break
        self.Q_gen = capacity((low + high) / 2)  # also the shares of the generators

    def _check_mode_header(self):
        """Mode and secondary flow of a plant with a header.

        Returns:
            float: heat of the secondary to the water (W): coils, process and losses (the
                heat of the pumps is in Q_pump).
        """
        Q_coils = self.Q_coils
        if self.on_off:
            if self.parameter("system_control").value == "LOAD_CONTROL":
                total = Q_coils + self.Q_process + self.Q_tank_loss  # a tank: its losses too
                self.mode = 1 if total < 0 else (-1 if total > 0 else 0)
            elif self.mode == 1:
                self.Q_process = min(self.Q_process, 0)
                Q_coils = min(Q_coils, 0)
            elif self.mode == -1:
                self.Q_process = max(self.Q_process, 0)
                Q_coils = max(Q_coils, 0)
            if not self.secondary_pumps:  # a tank without secondary pumps: the loads move it
                self.secondary_flow = self.coils_flow
            elif self.variable_flow:
                design = self.secondary_design_flow
                self.secondary_flow = min(max(self.coils_flow, self.minimum_flow * design), design)
            elif self.parameter("pump_operation").value == "ON_LOAD" and self.Q_process + Q_coils == 0:
                self.secondary_flow = 0
            else:
                self.secondary_flow = self.secondary_design_flow
        else:
            self.secondary_flow = 0
        self.Q_coils = Q_coils
        self.water_flow = self.secondary_flow
        self.Q_pump_secondary = sum(
            p.get_heat_gain(f) for p, f in zip(self.secondary_pumps, self._secondary_pump_flows())
            if f > 0
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
        self.T_WCO = (self.T_S + (Q_sec - self.Q_tank_loss) / (self.rho_cp * m_s)
                      if m_s > 0 else self.T_S)
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
        self.Q_dhw_used = self.Q_dhw
        self.Q_dhw = 0
        self.Q_heat_used, self.Q_heat = self.Q_heat, 0
        self.Q_cool_used, self.Q_cool = self.Q_cool, 0
        self.coils_flow_used = self.coils_flow
        self.coils_flow = 0
        self.priority_used = 0.0  # the DHW loads take their heat again

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
                    self._at_capacity(1, Q_required)
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
                    self._at_capacity(-1, -Q_required)

    def _at_capacity(self, mode, Q_required):
        """The generators cannot reach the setpoint: they give their full capacity and
        the water leaves them at another temperature, where their capacity is another
        (that of a heat pump depends on it). The temperature T of the water must satisfy
        the balance T = T_pre + (capacity(T) + rest) / C: it is found by bisection
        between the setpoint and the temperature without generators, where the
        difference changes sign (a fixed point may not converge with little water).
        If the capacity does not depend on the temperature (a boiler) there is nothing
        to find."""
        C = self.rho_cp * self.water_volume / self.delta_t
        rest = self.Q_pump + self.Q_coils + self.Q_process + self.Q_loss
        self.T_WGO = self.T_WGO_pre + (self.Q_gen + rest) / C
        if self.f_load == 0:  # no generator able to run
            return
        setpoint = self.T_heat_sp if mode == 1 else self.T_cool_sp

        def capacity(T):
            self.T_WGO = T
            return mode * self._generators_load(mode, float("inf"))[0]

        T1 = self.T_WGO
        if capacity(T1) == self.Q_gen:  # independent of the temperature
            self._generators_load(mode, Q_required)  # shares of the setpoint, as computed
            self.T_WGO = T1
            return

        def h(T):
            return T - self.T_WGO_pre - (capacity(T) + rest) / C

        T_free = self.T_WGO_pre + rest / C  # without generators
        low, high = sorted((setpoint, T_free))
        h_low = h(low)
        for _ in range(60):
            mid = (low + high) / 2
            h_mid = h(mid)
            if (h_mid > 0) == (h_low > 0):
                low, h_low = mid, h_mid
            else:
                high = mid
            if high - low < 1e-7:
                break
        T = (low + high) / 2
        self.Q_gen = capacity(T)  # also the shares of the generators at T
        self.T_WGO = self.T_WGO_pre + (self.Q_gen + rest) / C
        self.f_load = 1

    def limit_water_temperature(self, T):
        if T > self.max_water_temp:
            return self.max_water_temp
        elif T < self.min_water_temp:
            return self.min_water_temp
        else:   
            return T

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        if self.stratified:
            self._post_iteration_stratified(time_index)
            return
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
            self.variable("Q_loads").values[time_index] = 0
            self._store_coils(time_index, False)
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
            self.variable("Q_loads").values[time_index] = self.Q_coils_used
            self.variable("Q_dhw").values[time_index] = self.Q_dhw_used if self.mode == 1 else 0
            self._store_coils(time_index, True)
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
        for i, (g, Q_g, flow) in enumerate(zip(self.generators, self.Q_generators, self.generator_flows)):
            Q_g = Q_g if (running or (g.is_solar and self.on_off)) and flow > 0 else 0
            T_wi = self.T_WGI
            T_wo = T_wi + Q_g / (self.rho_cp * flow) if flow > 0 else T_wi
            if i in self.series_ops:
                Q_g, T_wi, T_wo, flow = self.series_ops[i]
            p, f, _ = g.set_operation(time_index, Q_g, T_wo, T_wi, flow, self.sequencing)
            power += p
            fuel += f
            pump_power += g.get_pump_power(flow)
        secondary_pump_power = sum(
            p.get_power(f) for p, f in zip(self.secondary_pumps, self._secondary_pump_flows())
            if f > 0
        ) if m_s > 0 else 0
        Q_gen = self.Q_gen if running else (self.Q_solar if self.on_off else 0)
        self.variable("Q_generators").values[time_index] = Q_gen
        self.variable("Q_loads").values[time_index] = self.Q_coils_used if m_s > 0 else 0
        self.variable("Q_dhw").values[time_index] = (
            self.Q_dhw_used if m_s > 0 and self.mode == 1 else 0)
        self._store_coils(time_index, m_s > 0)
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
        if self.tank is not None:
            self.tank.set_state(time_index, self.T_S, loss=-self.Q_tank_loss)

    def get_energy_use(self):
        """Electricity of its secondary pumps (water transport); its generators
        report their own energy.

        Returns:
            list: `Energy_use` items (W at each time step).
        """
        return split_dhw("ELECTRICITY", "WATER_TRANSPORT",
                         self.variable("secondary_pumps_power").values, self.dhw_share(),
                         mode_from_plant(self.variable("mode").values))

    def _store_coils(self, time_index, on):
        """Store the loads of the heating and cooling coils (0 if the water does not
        reach them; with SCHEDULE_CONTROL, those of the other mode are discarded)."""
        heat = self.Q_heat_used if on else 0
        cool = self.Q_cool_used if on else 0
        if self.parameter("system_control").value == "SCHEDULE_CONTROL":
            heat = heat if self.mode == 1 else 0
            cool = cool if self.mode == -1 else 0
        self.variable("Q_heating_coils").values[time_index] = heat
        self.variable("Q_cooling_coils").values[time_index] = cool

    def is_dhw_only(self):
        """True if all the loads of the plant are DHW: DHW demands and circuits with only
        DHW demands, no coils of air systems and no process load."""
        if getattr(self, "_dhw_only", None) is None:
            users = self.referring_components(
                ["DHW_demand", "HVAC_water_circuit", "HVAC_SZW_system", "HVAC_MZW_system"])
            self._dhw_only = (
                len(users) > 0
                and str(self.parameter("Q_process").value).strip() in ("0", "0.0", "")
                and all(u.parameter("type").value == "DHW_demand"
                        or (u.parameter("type").value == "HVAC_water_circuit" and u.is_dhw_only())
                        for u in users))
        return self._dhw_only

    def dhw_share(self):
        """Fraction of the heat given by the plant that goes to DHW demands, at each
        time step: the DHW part of the load of its coils over the load of its coils
        and processes, while heating.

        Returns:
            numpy.ndarray: values from 0 to 1.
        """
        mode = np.asarray(self.variable("mode").values)
        if self.is_dhw_only():  # also its losses and the heat stored in a tank
            return (mode == 1).astype(float)
        dhw = np.asarray(self.variable("Q_dhw").values, dtype=float)
        total = (np.asarray(self.variable("Q_loads").values, dtype=float)
                 + np.asarray(self.variable("Q_process").values, dtype=float))
        heating = (total < 0) & (mode == 1)
        share = np.divide(dhw, total, out=np.zeros_like(total), where=heating)
        return np.clip(share, 0, 1)
