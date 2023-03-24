
from opensimula.Property import Property
from opensimula.utils import print_message

class Property_box:
    def __init__(self):
        self._propiedades = []

    def append(self, property):
        """Append new Property"""
        # Solo comprobar que el objeto es del tipo project
        if (type(property) is Property):
            self._propiedades.append(property)
        else:
            print_message(str(property) + " is not a Component, it can't be added to Project.")


    def remove(self, property):
        self._propiedades.remove(property)

