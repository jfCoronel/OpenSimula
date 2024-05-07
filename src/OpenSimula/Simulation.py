from OpenSimula.Project import Project
import pandas as pd


class Simulation:
    """Simulation environment object for handling projects and print messages"""

    def __init__(self):
        self._projects_ = []
        self.console_print = True
        self._messages_ = []
        self._new_line_ = True

    def new_project(self, project_name):
        """Create new project in the Simulation

        Args:
            project_name (string): Name of the project to be added to the simulation environment
        """
        if self.project(project_name) == None:
            pro = Project(project_name, self)
            self._projects_.append(pro)
            return pro
        else:
            self.print("Error: There is already a project named: "+project_name)
            return None

    def del_project(self, project):
        """Delete project from Simulation

        Args:
            project (Project): Project to be removed from the simulation environment
        """
        self._projects_.remove(project)

    def project(self, name):
        """Find and return a project using its name

        Args:
            name (string): name of the project

        Returns:
            project (Project): project found, None if not found.
        """
        for pro in self._projects_:
            if pro.parameter("name").value == name:
                return pro
        return None

    def project_list(self):
        """Projects list in the simulation environment

        Returns:
            projects (Project): List of projects.
        """
        return self._projects_

    def project_dataframe(self):
        data = pd.DataFrame()
        pro_list = self.project_list()
        parameters = []
        if len(pro_list) > 0:
            for key, par in pro_list[0]._parameters_.items():
                parameters.append(key)
                param_array = []
                for pro in pro_list:
                    param_array.append(pro.parameter(key).value)
                data[key] = param_array
        return data

    def _repr_html_(self):
        html = "<h3>Simulation projects:</h3><ul>"
        html += self.project_dataframe().to_html()
        return html

    def print(self, message, add_new_line=True):
        """Print message

        Store de message in the message_list and print it console_print = True

        Args:
            message (string): message to print
            add_new_line (boolean, True): Add new line at the end, new message will be store in new message
                if False next message will be added to the last message
        """
        if self.console_print:
            if add_new_line:
                print(message)
            else:
                print(message, end="")

        if self._new_line_:
            self._messages_.append(message)
        else:
            self._messages_[-1] = self._messages_[-1] + message

        self._new_line_ = add_new_line

    def message_list(self):
        """Return the list of messages"""
        return self._messages_
