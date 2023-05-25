import opensimula as oms

p1_json = {
    "name": "pro 1",
    "type": "Project",
    "components": [
        {
            "type": "Test_component",
            "name": "comp 1",
            "boolean": True,
            "string": "Hola mundo",
            "int": 24,
            "float": 34.6,
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

p2_json = {
    "name": "pro 2",
    "type": "Project",
    "components": [
        {
            "type": "Test_component",
            "name": "comp 3",
            "component": "pro 1->comp 1",
            "component_list": ["pro 1->comp 1", "pro 1->comp 2"],
        }
    ],
}


sim = oms.Simulation()
p1 = oms.Project(sim)
p1.load_from_json(p1_json)

p2 = oms.Project(sim)
p2.load_from_json(p2_json)
p2.simulate()
