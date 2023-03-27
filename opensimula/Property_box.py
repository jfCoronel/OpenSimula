class Property_box:
    def __init__(self):
        self._propiedades = {}

    def addProperty(self, property):
        """add Property"""
        property._parent = self
        self._propiedades[property.name] = property

    def delProperty(self, property):
        self._propiedades.remove(property)

    @property
    def property(self):
        return self._propiedades
