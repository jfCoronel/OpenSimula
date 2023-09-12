class Simulation:
    """Simulation environment object for handling projects"""

    version = "0.0.1"

    def __init__(self):
        self._projects_ = []

    def add_project(self, project):
        """Add project to Simulation

        Args:
            project (Project): Project to be added to the simulation environment
        """
        project.parent = self
        self._projects_.append(project)

    def del_project(self, project):
        """Delete project from Simulation

        Args:
            project (Project): Project to be removed from the simulation environment
        """
        self._projects_.remove(project)

    def find_project(self, name):
        """Find project

        Args:
            name (string): name of the project

        Returns:
            project (Project): project found, None if not found.
        """
        for pro in self._projects_:
            if pro.parameter["name"].value == name:
                return pro
        return None

    @property
    def projects(self):
        """Projects list in the simulation environment

        Returns:
            projects (Project): List of projects.
        """
        return self._projects_

    def _repr_html_(self):
        html = "<h3>Simulation projects:</h3><ul>"
        for p in self._projects_:
            html += f"<li>{p.parameter['name'].value}</li>"
        html += "</ul>"
        return html
