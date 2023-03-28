from opensimula.Property import Property


class Property_float(Property):
    def __init__(self, name, value=0.0):
        Property.__init__(self, name, value)
