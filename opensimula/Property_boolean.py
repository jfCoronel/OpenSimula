from opensimula.Property import Property


class Property_boolean(Property):
    def __init__(self, name, value=False):
        Property.__init__(self, name, value)
