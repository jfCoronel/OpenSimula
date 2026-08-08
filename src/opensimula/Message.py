class Message:
    def __init__(self, text, level="ERROR"):
        self._text_ = text
        self._level_ = level   # ERROR, WARNING, INFO, CONSOLE

    @property
    def text(self):
        return self._text_

    @property
    def level(self):
        return self._level_
    
    def print(self):
        if self.level == "CONSOLE":
            print(self.text)
        else:
            print(self.level + ": " + self.text)
        
