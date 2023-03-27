from opensimula.Property import Property


class Property_string(Property):
    def __init__(self, name, default_value="", value=""):
        Property.__init__(self, name, default_value, value)
