class Message:
    """Message of the simulation environment (error, warning or information)

    Messages are added with `Simulation.message()` and listed with
    `Simulation.message_list()`.
    """

    def __init__(self, text, level="ERROR"):
        """Create new message

        Args:
            text (str): text of the message
            level (str, optional): "ERROR", "WARNING", "INFO" or "CONSOLE". Defaults to
                "ERROR".
        """
        self._text_ = text
        self._level_ = level   # ERROR, WARNING, INFO, CONSOLE

    @property
    def text(self):
        """str: text of the message"""
        return self._text_

    @property
    def level(self):
        """str: "ERROR", "WARNING", "INFO" or "CONSOLE" """
        return self._level_
    
    def print(self):
        """Print the message, preceded by its level unless it is "CONSOLE" """
        if self.level == "CONSOLE":
            print(self.text)
        else:
            print(self.level + ": " + self.text)
        
