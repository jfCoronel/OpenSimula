class Child():
    """Objects with parent"""

    def __init__(self):
        self._parent = None

    @property
    def parent(self):
        return self._parent
