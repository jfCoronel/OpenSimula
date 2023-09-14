import opensimula as oms

p1_dic = {
    "name": "project 1",
    "type": "Project",
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
        },
    ],
}

p2_dic = {
    "name": "project 2",
    "type": "Project",
    "components": [
        {
            "type": "Test_component",
            "name": "comp 3",
            "component": "project 1->comp 1",
            "component_list": ["project 1->comp 1", "project 1->comp 2"],
        }
    ],
}


sim = oms.Simulation()
p1 = oms.Project(sim)
p1.read_dict(p1_dic)

p2 = oms.Project(sim)
p2.read_dict(p2_dic)
p2.simulate()
