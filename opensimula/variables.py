from opensimula.Child import Child

# _________________ Variable ___________________________


class Variable(Child):
    def __init__(self, name):
        Child.__init__(self)
        self._name_ = name
