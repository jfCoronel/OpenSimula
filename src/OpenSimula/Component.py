import pandas as pd
from OpenSimula.Parameter_container import Parameter_container
from OpenSimula.Parameters import Parameter_string


class Component(Parameter_container):
    """Base Class for all the components"""

    def __init__(self, name, proj):
        Parameter_container.__init__(self, proj._sim_)
        self._variables_ = {}
        self.add_parameter(Parameter_string("type", "Component"))
        self.parameter("name").value = name
        self.parameter("description").value = "Description of the component"
        proj._add_component_(self)
        self._project_ = proj

    def project(self):
        return self._project_

    def simulation(self):
        return self._sim_
    
    def print(self, msg):
        self._sim_.print(msg)

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

    def get_all_referenced_components(self):
        """Get list of all referenced components, first itself. Look recursively at the referenced components

        Returns:
            component_list (component[])
        """
        comp_list = [self]
        for key, value in self.parameter_dict().items():
            if value.type == "Parameter_component":
                if value.component is not None:
                    sublist = value.component.get_all_referenced_components()
                    for subcomp in sublist:
                        comp_list.append(subcomp)
            if value.type == "Parameter_component_list":
                for comp in value.component:
                    if comp is not None:
                        sublist = comp.get_all_referenced_components()
                        for subcomp in sublist:
                            comp_list.append(subcomp)
        return comp_list

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
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        pass

    def post_simulation(self):
        pass

    def pre_iteration(self, time_index, date):
        pass

    def iteration(self, time_index, date):
        return True

    def post_iteration(self, time_index, date):
        pass

    def _repr_html_(self):
        html = f"<h3>Component: {self.parameter('name').value}</h3><p>{self.parameter('description').value}</p>"
        html += "<strong>Parameters:</strong>"
        html += self.parameter_dataframe().to_html()
        if (len(self._variables_)>0):
            html += "<br/><strong>Variables:</strong>"
            html += self.variable_dataframe().head(10).to_html()
        return html

