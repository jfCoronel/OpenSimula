# ____________ Child ________________________


class Child():
    """Objects with parent"""

    def __init__(self, parent=None):
        self._parent = parent

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent):
        self._parent = parent
