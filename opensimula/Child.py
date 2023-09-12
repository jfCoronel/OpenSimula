# ____________ Child ________________________


class Child():
    """Objects with parent
    
    Superclass for Paramaters an Variables
    """

    def __init__(self, parent=None):
        self._parent_ = parent

    @property
    def parent(self):
        return self._parent_

    @parent.setter
    def parent(self, parent):
        self._parent_ = parent
