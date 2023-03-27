from opensimula.Property import Property


class Property_boolean(Property):
    def __init__(self, name, default_value=False, value=False):
        Property.__init__(self, name, default_value, value)
