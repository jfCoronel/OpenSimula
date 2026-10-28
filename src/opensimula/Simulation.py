from opensimula.Project import Project
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots


class Simulation:
    """Simulation environment object for handling projects and print messages

    It is the entry point of every OpenSimula program:

    ```python
    import opensimula as osm

    sim = osm.Simulation()
    pro = sim.new_project("Project one")
    pro.read_json("project.json")
    pro.simulate()
    ```

    Attributes:
        console_print (bool): Print the messages in the console when they are added.
            Defaults to True.
    """

    def __init__(self):
        self._projects_ = []
        self.console_print = True
        self._messages_ = []

    def new_project(self, project_name):
        """Create new project in the Simulation

        Args:
            project_name (str): Name of the project to be added to the simulation environment

        Returns:
            Project: The new project, None if there is already a project with that name.
        """
        if self.project(project_name) is None:
            pro = Project(project_name, self)
            self._projects_.append(pro)
            return pro
        else:
            self.message("Error: There is already a project named: "+project_name)
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
            name (str): name of the project

        Returns:
            Project: project found, None if not found.
        """
        for pro in self._projects_:
            if pro.parameter("name").value == name:
                return pro
        return None

    def project_list(self):
        """Projects list in the simulation environment

        Returns:
            list of Project: Projects of the simulation environment.
        """
        return self._projects_

    def project_dataframe(self, string_format=False):
        """Parameters of all the projects as a table

        Args:
            string_format (bool, optional): Convert every value to string. Defaults to False.

        Returns:
            pandas.DataFrame: One row per project, one column per parameter.
        """
        data = pd.DataFrame()
        pro_list = self.project_list()
        parameters = []
        if len(pro_list) > 0:
            for key, par in pro_list[0]._parameters_.items():
                parameters.append(key)
                param_array = []
                for pro in pro_list:
                    if string_format:
                        param_array.append(str(pro.parameter(key).value))
                    else:
                        param_array.append(pro.parameter(key).value)
                data[key] = param_array
        return data

    def _repr_html_(self):
        html = "<h3>Simulation projects:</h3><ul>"
        html += self.project_dataframe().to_html()
        return html

    def message(self, message):
        """Add new message

        Store de message in the message_list and print if console_print = True

        Args:
            message (Message): message to add
        """
        self._messages_.append(message)
        if self.console_print:
            message.print()
 
    def message_list(self):
        """List of messages

        Returns:
            list of Message: Messages added with message(), in order.
        """
        return self._messages_

    def plot(self, dates, variables, names=[], axis=[], frequency=None, value="mean",interval=None):
        """Draw variables graph (using plotly)

        Args:
            dates (array of datetime): Dates of the values, usually `project.dates()`.
            variables (list of Variable): Variables to draw.
            names (list of str, optional): Names of the series; variables beyond the list are
                named "component:variable". Defaults to [].
            axis (list of int, optional): y axis (1 or 2) of each variable; variables beyond the
                list use the first axis. Defaults to [].
            frequency (None or str, optional): frequency of the values: None, "hourly", "daily", "monthly", "yearly". Defaults to None.
            value (str, optional): "mean", "sum", "sum_pos", "sum_neg", "max" or "min". Defaults to "mean".
            interval (None or list of two dates): List with the start and end dates of the period to be included in the dataframe, if the value is None all values are included.
        """
        series = {}
        series["date"] = dates
        for i in range(len(variables)):
            if i < len(names):
                series[names[i]] = variables[i].values
            else:
                if variables[i].parent is not None:
                    series[variables[i].parent.parameter(
                        "name").value+":"+variables[i].key] = variables[i].values
                else:
                    series[variables[i].key] = variables[i].values
        data = pd.DataFrame(series)
        if frequency is not None:
            freq={"hourly": "h", "daily": "D", "monthly": "ME", "yearly": "YE"}
            if value == "mean":
                data = data.resample(freq[frequency], on='date').mean()
            elif value == "sum":
                data = data.resample(freq[frequency], on='date').sum()
            elif value == "sum_pos":
                data = data.resample(freq[frequency], on='date').apply(lambda x: x.clip(lower=0).sum())
            elif value == "sum_neg":
                data = data.resample(freq[frequency], on='date').apply(lambda x: x.clip(upper=0).sum())
            elif value == "max":
                data = data.resample(freq[frequency], on='date').max()
            elif value == "min":
                data = data.resample(freq[frequency], on='date').min()
            data["date"] = data.index
        if interval is not None:
            data = data[(data['date'] > interval[0]) &
                        (data['date'] < interval[1])]


        subfig = make_subplots(specs=[[{"secondary_y": True}]])

        for i in range(len(variables)):
            if i < len(names):
                name = names[i]
            else:
                if variables[i].parent is not None:
                    name = variables[i].parent.parameter(
                        "name").value+":"+variables[i].key
                else:
                    name = variables[i].key
            fig = px.line(data, x='date', y=name)
            fig.for_each_trace(lambda t: t.update(name=name))
            fig.update_traces(showlegend=True)
            if i < len(axis):
                if (axis[i] == 2):
                    fig.update_traces(yaxis="y2")
            subfig.add_traces(fig.data)

        subfig.for_each_trace(lambda t: t.update(
            line=dict(color=t.marker.color)))
        # fig.update_traces(showlegend=True)
        subfig.show()

