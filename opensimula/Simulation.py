import datetime as dt


class Simulation():
    """Simulation contains a list of Projects"""
    version = '0.0.1'

    def __init__(self):
        """Simulation enviroment, contains a list of Projects"""
        self._projects_ = []
        self._time_step_ = 600  # 10 min
        self._init_seconds_ = dt.datetime(2001, 1, 1).timestamp()

    def add_project(self, project):
        """Add project to Simulation"""
        project.parent = self
        self._projects_.append(project)

    def del_project(self, project):
        self._projects_.remove(project)

    def find_project(self, name):
        for pro in self._projects_:
            if (pro.parameter['name'] == name):
                return pro
        return None

    @property
    def projects(self):
        return self._projects_

    @property
    def time_step(self):
        """Time step in seconds"""
        return self._time_step_

    def message(self, msg):
        """Function to print all the messages"""
        print(str(msg))
