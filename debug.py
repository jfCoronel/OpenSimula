import OpenSimula.Simulation as Simulation
import OpenSimula.Simulation as Simulation

p1_dic = {
    "name": "project 1",
    "components": [
        {
            "type": "Test_component",
            "name": "comp 1",
            "boolean": True,
            "string": "Hola mundo",
            "int": 24,
            "float": 34.5,
            "options": "Two",
            "boolean_list": [True, True],
            "string_list": ["Hola 1", "Hola 2"],
            "int_list": [1, 2],
            "float_list": [1.1, 2.1],
            "options_list": ["Two", "Two"],
        },
        {
            "type": "Test_component",
            "name": "comp 2",
            "boolean": True,
            "string": "Hola mundo",
            "int": 24,
            "float": 34.6,
            "options": "Two",
            "component": "comp 1",
            "variable": "t_1 = comp 1.t"
        },
    ],
}

p2_dic = {
    "name": "project 2",
    "components": [
        {
            "type": "Test_component",
            "name": "comp 3",
            "component": "project 1->comp 1",
            "component_list": ["project 1->comp 1", "project 1->comp 2"],
            "variable": "t_1 = project 1->comp 1.t",
            "variable_list": ["t_2 = project 1->comp 1.t","t_3 = project 1->comp 2.t"],
            "math_exp": "4 * t_1 ",
            "math_exp_list": ["6 * t_2 ","ln(23)"]
        }
    ],
}

sim = Simulation()
p1 = sim.new_project("p1")
p1.read_dict(p1_dic)
p2 = sim.new_project("p2")
p2.read_dict(p2_dic)
sim