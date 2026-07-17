import copy
import opensimula as osim
import pytest

process_water_system_dict = {
    "name": "Process water system",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "simulation_file_met": "Sevilla",
    "components": [
        {
            "type": "File_met",
            "name": "Sevilla",
            "file_type": "MET",
            "file_name": "mets/sevilla.met"
        },
        {
            "type": "File_data",
            "name": "process_load",
            "file_type": "CSV",
            "file_name": "jupyter_test/process_load.csv",
            "file_step": "SIMULATION"
        },
        {
            "type": "Day_schedule",
            "name": "working_day",
            "time_steps": [8*3600, 9*3600],
            "values": [0, 1, 0],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "off_day",
            "time_steps": [],
            "values": [0],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "heating_day",
            "time_steps": [],
            "values": [1],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "cooling_day",
            "time_steps": [],
            "values": [-1],
            "interpolation": "STEP",
        },
        {
            "type": "Week_schedule",
            "name": "working_week",
            "days_schedules": [
                "working_day"
            ],
        },
        {
            "type": "Week_schedule",
            "name": "off_week",
            "days_schedules": [
                "off_day"
            ],
        },
        {
            "type": "Week_schedule",
            "name": "heating_week",
            "days_schedules": [
                "heating_day"
            ],
        },
        {
            "type": "Week_schedule",
            "name": "cooling_week",
            "days_schedules": [
                "cooling_day"
            ],
        },
        {
            "type": "Year_schedule",
            "name": "on_schedule",
            "periods": [],
            "weeks_schedules": ["working_week"],
        },
        {
            "type": "Year_schedule",
            "name": "mode_schedule",
            "periods": ["01/03", "01/11"],
            "weeks_schedules": ["heating_week", "cooling_week", "heating_week"],
        },
        {
            "type": "Pump",
            "name": "pump",
            "nominal_water_flow": 0.4137,
            "nominal_pressure": 100000,
            "nominal_power": 70,
        },
        {
            "type": "Chiller_heat_pump",
            "name": "heat_pump",
            "chiller_type": "CHILLER_HEAT_PUMP",
            "nominal_cooling_capacity": 8000,
            "nominal_cooling_power": 4000,
            "nominal_heating_capacity": 9000,
            "nominal_heating_power": 4500,
            "nominal_water_flow": 0.4137
        },
        {
            "type": "HVAC_water_system",
            "name": "water_system",
            "water_thermal_generator": "heat_pump",
            "pump": "pump",
            "design_water_flow": 0.4137,
            "heating_water_setpoint": "50",
            "cooling_water_setpoint": "7",
            "total_water_volume": 0.1,
            "system_on_off": "g",
            "pump_operation": "ON_LOAD",
            "system_control": "SCHEDULE_CONTROL",
            "system_mode": "f",
            "input_variables": ["Q = process_load.Q", "f = mode_schedule.values", "g = on_schedule.values"],
            "Q_process": "Q",
        }
    ]
}

# High load: generator undersized (Q_process = 2.5*Q)
high_load_water_system_dict = copy.deepcopy(process_water_system_dict)
for _c in high_load_water_system_dict["components"]:
    if _c["name"] == "water_system":
        _c["Q_process"] = "2.5*Q"

# Losses: Q_loss = 20*(22-T_w) if m_w > 0 else 0.2*(22-T_w)
losses_water_system_dict = copy.deepcopy(process_water_system_dict)
for _c in losses_water_system_dict["components"]:
    if _c["name"] == "water_system":
        _c["Q_loss"] = " 20*(22-T_w) if m_w > 0 else 0.2*(22-T_w)"


def _simulate_water_system(project_dict):
    sim = osim.Simulation()
    pro = sim.new_project("pro")
    pro.read_dict(project_dict)
    pro.simulate()
    return pro.component("water_system")


def test_HVAC_water_system_process_load():
    system = _simulate_water_system(process_water_system_dict)

    yearly_df = system.variable_dataframe(
        frequency="yearly", value="sum", pos_neg_columns=["Q_gen", "Q_process", "delta_U"]
    )

    cooling_load = yearly_df["Q_process_pos"].values[0] / 1e6
    heating_load = yearly_df["Q_process_neg"].values[0] / 1e6
    pump_heat = yearly_df["Q_pump"].values[0] / 1e6
    losses = yearly_df["Q_loss"].values[0] / 1e6
    delta_U_pos = yearly_df["delta_U_pos"].values[0] / 1e6
    delta_U_neg = yearly_df["delta_U_neg"].values[0] / 1e6
    cooling_generation = yearly_df["Q_gen_neg"].values[0] / 1e6
    heating_generation = yearly_df["Q_gen_pos"].values[0] / 1e6

    assert cooling_load == pytest.approx(2.246582)
    assert heating_load == pytest.approx(-0.12052)
    assert pump_heat == pytest.approx(0.12026)
    assert losses == pytest.approx(0.0)
    assert delta_U_pos == pytest.approx(0.008737086, rel=1e-5)
    assert delta_U_neg == pytest.approx(-0.005335120, rel=1e-5)
    assert cooling_generation == pytest.approx(-2.460499, rel=1e-5)
    assert heating_generation == pytest.approx(0.116618007, rel=1e-5)

    T_WGO = system.variable("T_WGO").values
    T_WGI = system.variable("T_WGI").values

    assert T_WGO.max() == pytest.approx(50.54919761)
    assert T_WGO.min() == pytest.approx(7.0)
    assert T_WGI.max() == pytest.approx(50.58607334)
    assert T_WGI.min() == pytest.approx(7.040288469)


def test_HVAC_water_system_high_load():
    system = _simulate_water_system(high_load_water_system_dict)

    yearly_df = system.variable_dataframe(
        frequency="yearly", value="sum", pos_neg_columns=["Q_gen", "Q_process", "delta_U"]
    )

    cooling_load = yearly_df["Q_process_pos"].values[0] / 1e6
    heating_load = yearly_df["Q_process_neg"].values[0] / 1e6
    pump_heat = yearly_df["Q_pump"].values[0] / 1e6
    losses = yearly_df["Q_loss"].values[0] / 1e6
    delta_U_pos = yearly_df["delta_U_pos"].values[0] / 1e6
    delta_U_neg = yearly_df["delta_U_neg"].values[0] / 1e6
    cooling_generation = yearly_df["Q_gen_neg"].values[0] / 1e6
    heating_generation = yearly_df["Q_gen_pos"].values[0] / 1e6

    assert cooling_load == pytest.approx(5.8690325)
    assert heating_load == pytest.approx(-0.3013)
    assert pump_heat == pytest.approx(0.12026)
    assert losses == pytest.approx(0.0)
    assert delta_U_pos == pytest.approx(0.0396344596, rel=1e-5)
    assert delta_U_neg == pytest.approx(-0.0364659297, rel=1e-5)
    assert cooling_generation == pytest.approx(-5.982142760, rel=1e-5)
    assert heating_generation == pytest.approx(0.297356468, rel=1e-5)

    T_WGO = system.variable("T_WGO").values
    T_WGI = system.variable("T_WGI").values

    # Generator undersized: outlet temperature cannot reach the setpoints
    assert T_WGO.max() == pytest.approx(69.50618103)
    assert T_WGO.min() == pytest.approx(7.0)
    assert T_WGI.max() == pytest.approx(75.29645168)
    assert T_WGI.min() == pytest.approx(7.040288586)


def test_HVAC_water_system_losses():
    system = _simulate_water_system(losses_water_system_dict)

    yearly_df = system.variable_dataframe(
        frequency="yearly", value="sum", pos_neg_columns=["Q_gen", "Q_process", "delta_U"]
    )

    cooling_load = yearly_df["Q_process_pos"].values[0] / 1e6
    heating_load = yearly_df["Q_process_neg"].values[0] / 1e6
    pump_heat = yearly_df["Q_pump"].values[0] / 1e6
    losses = yearly_df["Q_loss"].values[0] / 1e6
    delta_U_pos = yearly_df["delta_U_pos"].values[0] / 1e6
    delta_U_neg = yearly_df["delta_U_neg"].values[0] / 1e6
    cooling_generation = yearly_df["Q_gen_neg"].values[0] / 1e6
    heating_generation = yearly_df["Q_gen_pos"].values[0] / 1e6

    assert cooling_load == pytest.approx(2.347613)
    assert heating_load == pytest.approx(-0.120633)
    assert pump_heat == pytest.approx(0.12026)
    assert losses == pytest.approx(0.345808280, rel=1e-5)
    assert delta_U_pos == pytest.approx(0.0350031147, rel=1e-5)
    assert delta_U_neg == pytest.approx(-0.0317224968, rel=1e-5)
    assert cooling_generation == pytest.approx(-2.922284365, rel=1e-5)
    assert heating_generation == pytest.approx(0.228625429, rel=1e-5)

    T_WGO = system.variable("T_WGO").values
    T_WGI = system.variable("T_WGI").values

    assert T_WGO.max() == pytest.approx(50.0)
    assert T_WGO.min() == pytest.approx(7.0)
    assert T_WGI.max() == pytest.approx(49.719955965)
    assert T_WGI.min() == pytest.approx(7.211026683)
