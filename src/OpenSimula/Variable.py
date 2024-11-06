import numpy as np
from OpenSimula.Child import Child

# _________________ Variable ___________________________


class Variable(Child):
    def __init__(self, key, unit="", description=""):
        Child.__init__(self)
        self._key_ = key
        self._unit_ = unit
        self._description_ = description
        self._values_ = None
        self._sim_ = None

    @property
    def key(self):
        return self._key_

    @key.setter
    def key(self, key):
        self._key_ = key

    @property
    def values(self):
        return self._values_

    @property
    def unit(self):
        return self._unit_

    @property
    def description(self):
        return self._description_

    def initialise(self, n, default=0.0):
        self._values_ = np.full(n, default)
