# OpenSimula — Construction & Building Components

## Construction Materials

```python
# Material — thermal properties
{"type": "Material", "name": "brick",
 "conductivity": 0.9,    # W/(m·K)
 "density": 1800,        # kg/m³
 "specific_heat": 840}   # J/(kg·K)
# OR use thermal resistance: "use_resistance": True, "thermal_resistance": 0.2  [m²·K/W]

# Construction — multi-layer assembly
{"type": "Construction", "name": "ext_wall",
 "solar_alpha": 0.6,     # exterior solar absorptance
 "lw_epsilon": 0.9,      # exterior long-wave emissivity
 "materials": ["plaster", "brick", "insulation", "plaster"],
 "thicknesses": [0.015, 0.20, 0.08, 0.015]}   # meters, one per material

# Glazing — window glass
{"type": "Glazing", "name": "dbl_glass",
 "solar_tau": 0.589,   # solar transmittance
 "solar_rho": 0.117,   # solar reflectance
 "lw_epsilon": 0.837,
 "g": 0.65,            # total solar energy transmittance (SHGC)
 "U": 2.8}             # W/(m²·K)

# Frame — window frame
{"type": "Frame", "name": "alu_frame",
 "solar_alpha": 0.6, "lw_epsilon": 0.9,
 "thermal_resistance": 0.5}  # m²·K/W

# Opening_type — complete window/door assembly
{"type": "Opening_type", "name": "window_type",
 "glazing": "dbl_glass", "frame": "alu_frame",
 "glazing_fraction": 0.8, "frame_fraction": 0.2}
```

## Building Components

```python
# Building — container for geometry and initial conditions
{"type": "Building", "name": "building",
 "azimuth": 0,              # degrees: 0=North, 90=East, 180=South, 270=West
 "ref_point": [0, 0, 0],    # [x, y, z] global reference point in meters
 "initial_temperature": 20, # °C
 "initial_humidity": 7.3}   # g/kg a.s.

# Space_type — occupancy and internal gains definition
{"type": "Space_type", "name": "office",
 "input_variables": ["f = my_year.values"],  # schedule alias
 "people_density": "0.1 * f",      # persons/m², math expression
 "people_sensible": 75,            # W/person
 "people_latent": 55,              # W/person
 "people_radiant_fraction": 0.5,
 "light_density": "10 * f",        # W/m²
 "light_radiant_fraction": 0.5,
 "other_gains_density": "5 * f",   # W/m²
 "other_gains_radiant_fraction": 0.4,
 "other_gains_latent_fraction": 0.0,
 "infiltration": "0.5 * f"}        # ACH (air changes per hour)
# Variables: Q_people_conv, Q_people_rad, Q_people_lat,
#            Q_light_conv, Q_light_rad, Q_other_conv, Q_other_rad, Q_other_lat [W/m²]

# Space — thermal zone
{"type": "Space", "name": "zone_1",
 "building": "building",
 "space_type": "office",
 "floor_area": 50,          # m²
 "volume": 150,             # m³
 "furniture_weight": 0,     # kg/m² of floor area
 "convergence_DT": 0.01,    # K, temperature convergence tolerance
 "convergence_Dw": 0.01}    # g/kg, humidity convergence tolerance
# Variables: temperature [°C], humidity [g/kg a.s.], Q_infiltration [W],
#            Q_people, Q_light, Q_other, Q_solar, Q_surface_conv,
#            Q_surface_rad, Q_system, Q_system_latent [W], m_infiltration [kg/s]

# Building_surface — wall / roof / floor / slab
{"type": "Building_surface", "name": "south_wall",
 "shape": "RECTANGLE",    # or "POLYGON" → use "polygon": [[x,y],...] in local coords
 "width": 5.0,            # m (RECTANGLE only)
 "height": 3.0,           # m (RECTANGLE only)
 "ref_point": [0, 0, 0],  # local building coordinates [x, y, z]
 "azimuth": 180,          # degrees (180=South)
 "altitude": 90,          # degrees (90=vertical, 0=horizontal/roof)
 "surface_type": "EXTERIOR",  # "EXTERIOR","INTERIOR","UNDERGROUND","VIRTUAL"
 "construction": "ext_wall",
 "spaces": ["zone_1"],    # 1 space (EXTERIOR) or 2 (INTERIOR, one per side)
 "h_cv": [25, 7.7]}       # [exterior, interior] convective coefficients W/(m²·K)
# Variables: T_ext, T_int, T_surf_ext, T_surf_int [°C],
#            Q_cond, Q_cv_int, Q_cv_ext, Q_solar_abs,
#            Q_lw_rad_ext, Q_lw_rad_int [W], E_solar [W/m²]

# Opening — window or door set into a Building_surface
{"type": "Opening", "name": "south_window",
 "surface": "south_wall",
 "shape": "RECTANGLE",
 "width": 1.5, "height": 1.2,
 "ref_point": [1.0, 0.9, 0],   # position within the surface [local coords]
 "opening_type": "window_type",
 "setback": 0.1,               # m, setback from surface plane
 "h_cv": [25, 7.7]}
# Variables: T_ext, T_int, T_surf_ext, T_surf_int [°C], tau_solar,
#            Q_solar_trans, Q_cond, Q_cv_int, Q_cv_ext,
#            Q_lw_rad_ext, Q_lw_rad_int [W]

# Solar_surface — shading element (overhang, fin, neighbouring building)
{"type": "Solar_surface", "name": "overhang",
 "coordinate_system": "BUILDING",  # or "GLOBAL"
 "building": "building",
 "shape": "RECTANGLE",
 "width": 2.0, "height": 0.5,
 "ref_point": [0, 3.0, 0],
 "azimuth": 180, "altitude": 0,    # altitude=0 → horizontal
 "cast_shadows": True,
 "calculate_solar_radiation": False}
# Variables (only if calculate_solar_radiation=True): E_dir, E_dif [W/m²]
```
