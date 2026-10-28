import numpy as np
from opensimula.Child import Child

# _________________ Variable ___________________________


class Variable(Child):
    """Time series of a component, one value per time step of the simulation

    ```python
    t = pro.component("space_1").variable("temperature")
    t.values  # numpy array
    t.unit    # "°C"
    ```
    """

    def __init__(self, key, unit="", description=""):
        """Create new variable, without values until initialise()

        Args:
            key (str): key of the variable in its component
            unit (str, optional): unit. Defaults to "".
            description (str, optional): description. Defaults to "".
        """
        Child.__init__(self)
        self._key_ = key
        self._unit_ = unit
        self._description_ = description
        self._values_ = None
        self._sim_ = None

    @property
    def key(self):
        """str: key of the variable in its component"""
        return self._key_

    @key.setter
    def key(self, key):
        self._key_ = key

    @property
    def values(self):
        """numpy.ndarray: value of each time step"""
        return self._values_

    @values.setter
    def values(self, values):
        self._values_ = values

    @property
    def unit(self):
        """str: unit of the values"""
        return self._unit_

    @property
    def description(self):
        """str: description of the variable"""
        return self._description_

    def initialise(self, n, default=0.0):
        """Create the array of values

        Args:
            n (int): number of time steps
            default (float, optional): initial value. Defaults to 0.0.
        """
        self._values_ = np.full(n, default)
