def test_name_in_list(name, list):
    """Comprueba si el nombre no está en la lista"""
    for x in list:
        if (x.name == name):
            return test_name_in_list(name+'_', list)

    return name
