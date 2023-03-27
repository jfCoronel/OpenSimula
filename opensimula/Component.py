from opensimula.Child import Child
from opensimula.Property_box import Property_box
from opensimula.Variable_box import Variable_box


class Component(Child, Property_box, Variable_box):
    def __init__(self):
        Child.__init__(self)
        Property_box.__init__(self)
        Variable_box.__init__(self)
