import numpy as np
from opensimula.Child import Child

# _________________ Variable ___________________________


class Variable(Child):
    def __init__(self, key, n, unit="", default=0.0):
        Child.__init__(self)
        self._key_ = key
        self._unit_ = unit
        self._array_ = np.full(n, default)
        self._sim_ = None

    @property
    def key(self):
        return self._key_

    @key.setter
    def key(self, key):
        self._key_ = key

    @property
    def array(self):
        return self._array_

    @property
    def unit(self):
        return self._unit_
