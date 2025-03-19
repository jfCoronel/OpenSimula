def rhocp_water(T):
    """
    Returns: Liquid water rho*c_p at 1 atm (J/(m^3·K)), Cubic adjustment

    Paramaters:
        T: water temperature (ºC)
    """
    return (-6.5515e-08  * T**3 +7.6219e-06 * T**2 -1.8564e-03* T +  4.2125)*1e6
    