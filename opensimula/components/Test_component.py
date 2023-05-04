from opensimula.parameters import Parameter_boolean, Parameter_number, Parameter_string, Parameter_options, Parameter_component
from opensimula.Component import Component


class Test_component(Component):
    """Component for development testing"""

    def __init__(self):
        Component.__init__(self)
        self.parameter["type"].value = "Test_component"
        self.parameter["name"].value = "Test_component_x"
        self.add_parameter(Parameter_string("string", "Hello World"))
        self.add_parameter(Parameter_number("number", 100, "m"))
        self.add_parameter(Parameter_boolean("boolean", False))
        self.add_parameter(Parameter_options(
            "options", "One", ["One", "Two", "Three"]))
        self.add_parameter(Parameter_component("component", "not_defined"))

    def check(self):
        # Test if component reference exist
        self.parameter['component'].findComponent()
        self.parameter['component'].info()
        if (self.parameter['component'].component == None):
            return 1
        else:
            return 0
