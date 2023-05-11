from opensimula.parameters import (
    Parameter_boolean,
    Parameter_float,
    Parameter_int,
    Parameter_string,
    Parameter_options,
    Parameter_component,
)
from opensimula.Component import Component


class Test_component(Component):
    """Component for development testing"""

    def __init__(self):
        Component.__init__(self)
        self.parameter["type"].value = "Test_component"
        self.parameter["name"].value = "Test_component_x"
        self.parameter["description"].value = "Dummy component for testing"

        self.add_parameter(Parameter_string("string", "Hello World"))
        self.add_parameter(Parameter_float("int", 100, "h"))
        self.add_parameter(Parameter_float("float", 100.56, "m"))
        self.add_parameter(Parameter_boolean("boolean", False))
        self.add_parameter(Parameter_options("options", "One", ["One", "Two", "Three"]))
        self.add_parameter(Parameter_component("component", "not_defined"))

    def check(self):
        # Test if component reference exist
        component = self.parameter["component"].findComponent()
        if component == None:
            print(
                "Error in component: ",
                self.parameter["name"].value,
                ", type: ",
                self.parameter["type"].value,
            )
            print(
                "   component: ",
                self.parameter["component"].value,
                " component not found",
            )
            return 1
        else:
            return 0
