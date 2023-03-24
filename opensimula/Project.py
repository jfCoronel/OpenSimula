from opensimula.Component import Component
from opensimula.Property_box import Property_box
from opensimula.utils import print_message

class Project(Property_box):
    def __init__(self):
        self._componentes = []

    def append(self, component):
        """Append new component to Project"""
        # Solo comprobar que el objeto es del tipo project
        if (type(component) is Component):
            self._componentes.append(component)
        else:
            print_message(str(component) + " is not a Component, it can't be added to Project.")


    def remove(self, component):
        self._componentes.remove(component)

