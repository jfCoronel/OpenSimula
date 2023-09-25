import pandas as pd
from opensimula.Parameter_container import Parameter_container
from opensimula.Parameters import Parameter_string


class Component(Parameter_container):
    """Base Class for all the components"""

    def __init__(self, proj):
        Parameter_container.__init__(self, proj._sim_)
        self._variables_ = {}
        self.add_parameter(Parameter_string("type", "Component"))
        self.parameter("name").value = "Component_X"
        self.parameter("description").value = "Description of the component"
        self._project_ = proj

    def project(self):
        return self._project_

    def simulation(self):
        return self._sim_

    def add_variable(self, variable):
        """add new Variable"""
        variable._parent = self
        variable._sim_ = self._sim_
        self._variables_[variable.key] = variable

    def del_variable(self, variable):
        self._variables_.remove(variable)

    def del_all_variables(self):
        self._variables_ = {}

    def variable(self, key):
        return self._variables_[key]

    def variable_dict(self):
        return self._variables_

    def variable_dataframe(self):
        series = {}
        series["date"] = self.project().dates_array()
        for key, var in self._variables_.items():
            if var.unit == "":
                series[key] = var.array
            else:
                series[key + " [" + var.unit + "]"] = var.array
        data = pd.DataFrame(series)
        return data

    # ____________ Functions that must be overwriten for time simulation _________________

    def check(self):
        """Check if all is correct

        Returns:
            errors (string list): List of errors
        """
        errors = []
        # Parameter errors
        for key, value in self.parameter_dict().items():
            param_error = value.check()
            for e in param_error:
                errors.append(e)
        ext_comp_list = self._get_external_component_list_()
        # External component errors
        for comp in ext_comp_list:
            ext_comp_error = comp.check()
            for e in ext_comp_error:
                errors.append(e)
        return errors

    def pre_simulation(self, n_time_steps):
        self._external_component_list_ = self._get_external_component_list_()
        for comp in self._external_component_list_:
            comp.pre_simulation(n_time_steps)

    def post_simulation(self):
        for comp in self._external_component_list_:
            comp.post_simulation()

    def pre_iteration(self, time_index, date):
        for comp in self._external_component_list_:
            comp.pre_iteration(time_index, date)

    def iteration(self, time_index, date):
        return_value = True
        for comp in self._external_component_list_:
            comp_return_value = comp.iteration(time_index, date)
            if comp_return_value == False:
                return_value = False
        return return_value

    def post_iteration(self, time_index, date):
        for comp in self._external_component_list_:
            comp.post_iteration(time_index, date)

    def _get_external_component_list_(self):
        ext_comp_list = []
        for key, value in self.parameter_dict().items():
            if value.type == "Parameter_component":
                if value.external:
                    ext_comp_list.append(value.component)
            if value.type == "Parameter_component_list":
                for i in range(len(value.value)):
                    if value.external[i]:
                        ext_comp_list.append(value.component[i])
        return ext_comp_list
