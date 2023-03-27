from opensimula.Child import Child
from opensimula.Property_box import Property_box
from opensimula.Variable_box import Variable_box


class Project(Child, Property_box, Variable_box):
    """Project contains a list of Components"""

    def __init__(self):
        Child.__init__(self)
        Property_box.__init__(self)
        Variable_box.__init__(self)
        self._componentes = []

    def addComponent(self, component):
        """Add component to the Project"""
        component._parent = self
        self._componentes.append(component)

    def delComponent(self, component):
        self._componentes.remove(component)

    @property
    def component(self):
        return self._componentes
