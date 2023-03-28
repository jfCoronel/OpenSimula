from opensimula.Child import Child
from opensimula.Property_box import Property_box
from opensimula.Variable_box import Variable_box
from opensimula.Property_string import Property_string
from opensimula.utils import print_message


class Component(Child, Property_box, Variable_box):
    def __init__(self):
        Child.__init__(self)
        Property_box.__init__(self)
        Variable_box.__init__(self)
        self.addProperty(Property_string("name", "Component  x"))

    def print(self):
        print_message(type(self).__name__ + ": ")
        for key, value in self.property.items():
            print_message(key + ": " + str(value.value))
