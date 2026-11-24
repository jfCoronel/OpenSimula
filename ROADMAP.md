# Development Roadmap

Working notes for resuming development on OpenSimula from any machine. This file is for
the maintainer, not end users — it is not part of the published docs (`mkdocs/`).

## Where things stand (2026-11-19)

- **v0.10.0 released (2026-11-19)**: PyPI, GitHub release `v0.10.0`, Zenodo version DOI
  10.5281/zenodo.24369425. Water plants (`Boiler`, `HVAC_water_generator` with several
  generators, units and sequencing, header with secondary pumps, `HVAC_water_circuit`),
  `Load_space` (zones from load records, `Thermal_zone` base class), MZW connected to its
  water systems, gallery of nine examples, docs (user guide "HVAC systems and water plants"
  with an SVG diagram, release notes page with the whole history and the upgrade from 0.9,
  top bar grouped in one line). Breaks the compatibility of `HVAC_water_system`. Tests 220,
  `validate.py --check` full: 0 changed. Details: sections "Planned: several generators..."
  and "Planned: `Load_space`..." below (PRs #44-#58).
- **Next (agreed 2026-11-19)**: CTE indicators. Design closed 2026-11-23 (section
  "Planned: `Energy_indicators`..." below): `Energy_indicators` (0.11), `Comfort_indicators`,
  `CTE_compliance` later. Later candidates: B6
  variable secondary flow and pump staging (0.11; moved ahead of DHW steps 2-3 on
  2026-11-24, see "B6: variable water flow"), small follow-ups (`File_data` dates,
  viewer CSV names with dots), HULC importer, marimo/WASM course. JOSS: wait (see memory),
  one combined paper update for 0.9 + 0.10 when an editor is assigned or with the ping at
  the end of November.

## Plan agreed 2026-11-24: systems for the importers

The HULC importer (CALENER-GT systems) should not be left half done: the usual systems of
HULC must exist first. The test building of the TFG (`edificio_pmt_atecyr_sis3.ctehexml`)
already has two that OpenSimula lacks: a DHW system (gas boiler, 120 l/day at 60 °C) and a
multisplit 4×1 (`SIS_Autonomo2`: outdoor unit `EQ_ED_UnidadExterior` with capacity /
power curves vs temperature and part load, "Defecto" curves of the CALENER-GT catalogue,
and indoor units `UT_ED_UnidadInterior` per zone). An importer of EnergyPlus IDF files
(through epJSON) would open OpenSimula to that community. Order agreed:

1. `CTE_compliance` HE0 (section below), in progress.
2. **DHW**: demand (l/day, hourly profile of Anejo D, use and mains temperature of
   Anejo G), storage tank with losses, generators (boiler, DHW heat pump, electric
   heater, combined boiler with DHW priority) and **solar thermal** (collector η0, a1,
   a2; needed for HE4).
3. **Water emitters**: radiators (Q = Q_nom·(ΔT/50)^n, EN 442, radiant part) and a
   simplified radiant floor, fed by water plants/circuits (boiler + radiators is the
   usual Spanish dwelling).
4. **Multizone direct expansion**: multisplit / VRF, one outdoor unit with curves and
   indoor units per zone (CALENER-GT / DOE-2 style; heat recovery VRF later).
5. **Ventilation**: mechanical ventilation with heat recovery and a primary-air AHU
   serving several zones together with local terminals (fan coils...).
6. **EnergyPlus IDF importer, phase 1** (can run in parallel): geometry, constructions,
   `Schedule:Compact`, internal gains, infiltration, `ZoneHVAC:IdealLoadsAirSystem` →
   `HVAC_perfect_system`; validation with the BESTEST / ASHRAE 140 IDFs of EnergyPlus
   (BSD-3). Phase 2: `HVACTemplate:*` and simple equipment (PTAC/PTHP → DX).
7. HULC importer, when 2-5 exist; more real `.ctehexml` files (residential, tertiary) to
   see which systems appear; the default curves are in `BDCatalogo.bdc`.
   **Test buildings** (pointed by the user 2026-11-24): the Guía de aplicación DB-HE 2019
   has five worked examples, each with its justification PDF and its HULC files
   (https://www.codigotecnico.org/Guias/GuiaHE2019.html): I vivienda unifamiliar mínima,
   II unifamiliar adosada, III vivienda colectiva en altura, IV local comercial, V
   edificio de oficinas (`Guia_aplicacion_DBHE2019_Ejemplos_I..V.pdf`,
   `Guia_Ejemplos_DBHE2019-*.zip`). Use them to check `CTE_compliance` (C_ep,nren,
   C_ep,tot, hours outside setpoint against HULC) and as the reference set of the HULC
   importer (which systems appear).

Later: water-cooled chillers and cooling towers, ground-source heat pumps, PV (HE5, monthly
balance with kexp = 0), district heating.

## Where things stood (2026-11-13)

- **v0.9.0 released (2026-11-13)**: PyPI, GitHub release `v0.9.0`, Zenodo version DOI
  10.5281/zenodo.24194954. Graphical interface (phases 1–4 below: results viewer with 3D
  view, graph view in the editor, `opensimula gui` app with the `gui` extra) and the fix of
  the surface temperatures of openings (PRs #31–#38). `validate.py --check`: 0 values
  changed. The JOSS paper could mention the GUI during the review.
- **Editor's plotly bundled (branch `fix/editor-plotly-bundled`)**: the editor no longer
  imports plotly from esm.sh; it asks Python (`{"type": "plotly"}`) and gets
  `static/plotly3d.js`, as the results viewer does, shared through `view3d.js`. Checked in
  Chrome with every request outside localhost blocked. Closes the "Known follow-up" on the
  VS Code CSP. Merged (PR #40).
- **Examples gallery (branch `feat/examples-gallery`)**: seven progressive projects in
  `src/opensimula/examples/` (01 schedules, 02 weather + Calculator, 03 walls, 04 windows and
  gains, 05 ideal system, 06 DX, 07 fan coil), case 600 box in Sevilla (`sevilla.met` shipped),
  each one the previous plus one idea, every component with a description. `opensimula
  examples [folder]` copies them (never overwrites). Docs page `mkdocs/examples.md` with one
  figure each (`mkdocs/img/examples/`, made by a one-off matplotlib script). Systems (05-07) work
  in office hours at 20/25 °C, with outdoor air, and the office use of 05-07 has infiltration
  only while closed (`0.5 * (1 - f)`); hours above 25.5 °C while open: ideal 0, DX 18, fan
  coil 2. The water loop uses LOAD_CONTROL: with SCHEDULE_CONTROL (two-pipe) the office
  overheats on sunny winter days. The box needs cooling all year (12 m² south glass), said in
  the docs. Tests in `test/test_examples.py`.
  Same branch: results viewer draws monthly/yearly values as bars (`barPaths` in
  `results.src.js`, grouped per period) and has the aggregations `sum_pos`/`sum_neg`; example
  05 adds a Calculator `loads` (heating_load/cooling_load, kW). **Core fix found here
  (own commit):** `Calculator` evaluated only in `pre_iteration`, so any variable computed
  during the time step (space loads, system power) was read as 0 (or the previous value);
  it now evaluates again in `post_iteration` (calculators are last in the order). No
  ASHRAE 140 case uses a Calculator. The DX unit of example 06 uses a cycling degradation
  `0.85 + 0.15 * F_load` (Cd = 0.15, EnergyPlus default) instead of the ASHRAE 140 CE curves,
  which made EER ~ F_load (mean EER 1.7, COP 0.6). The viewer has the aggregation
  `mean_nonzero` ("Mean without zeros"): EER/COP are 0 while the unit is off. Considered and
  left for later: storing NaN instead of 0 in HVAC_DX_system when off. The air-to-water heat
  pump of 07 has nominal EER 3.0 / COP 3.2 (was 2.0 / 2.0) and the same degradation; running
  EER 2.9, COP 2.4.
  **Second core fix found here (own commit):** `HVAC_water_system` reset `Q_coils` to 0 at the
  end of each iteration and then stored it, so the variable was always 0; the balance of the
  loop did use it, so no other result changes (ASHRAE 140 has no water systems: 0 changed).
  It now stores the load of the last iteration (`Q_coils_used`).

- **Graphical interface, plan agreed 2026-11-12**, in four phases: (1) results viewer as
  an anywidget for notebooks, (2) link it to the 3D view, (3) graph view of the components
  (boxes with their parameters) in the editor, (4) app through Marimo (`opensimula gui`).
  **Phase 1 done** (branch `feat/results-widget`): `pro.results()` →
  `editor/results.py` + `vendor/results.src.js` (uPlot 1.6.32 bundled with esbuild, no
  runtime imports). One chart per unit, fixed 8-colour palette, resampling and interval in
  Python, table and CSV, drag zoom / Shift+drag pan shared by all charts, configurable
  heights. Test notebook `jupyter_test/RESULTS_VIEWER.ipynb`. Note: uPlot's `setScale`
  hooks fire deferred, so syncing the range between charts must skip charts already at
  that range or they bounce it forever.
- **GUI phase 2 (branch `feat/results-3d`)**: 3D view in the results viewer
  (`show_3d`). Click a surface → opened in the variable list with its spaces; plotted
  surfaces drawn in their series colour, plotted spaces in the outline. plotly is shipped
  as `static/plotly3d.js` and sent by Python on first use (blob import, VS Code safe);
  3D helpers shared with the editor in `vendor/view3d.js`. Merged (PR #32), with × to close a chart and
  Shift+click on the legend to remove a variable.
- **GUI phase 2, step 2 (branch `feat/results-3d-color`)**: colour the 3D model by a
  surface variable (`color_variable`, `color_statistic` mean/max/min over the interval;
  sequential or diverging scale by sign). Merged (PR #33).
- **GUI phase 2, step 3 (branch `feat/results-3d-time`)**: "At cursor" colouring, the 3D
  model follows the time under the chart cursor (series of all surfaces sent as float32
  bytes, `surface_series`; restyle() per frame). Closes phase 2 (merged, PR #35).
- **GUI phase 3 (branch `feat/editor-graph`)**: graph view of the components in the
  editor (`vendor/graph.js`, plain SVG): boxes with their reference parameters, arrows to
  the referenced components, layered layout (barycentre ordering), types with > 6 components
  folded, selection linked with the list/form/3D (a click on the background clears it),
  "selected and what it uses" filter, families of the legend switch their components on/off.
  Merged (PR #36).
- **GUI phase 4 (branch `feat/gui-app`)**: `opensimula gui [project.json]` (entry point in
  `opensimula/gui/__init__.py`, `gui` extra with marimo) runs `gui/app.py`, a marimo notebook
  as an app: open/new project, editor, Simulate (apply + check + simulate, problems listed),
  Save (the document, to JSON), results viewer rebuilt after each run. Only the cell that
  creates a wrapped widget names it: a cell naming a marimo UI element reruns on every edit.
  Relative paths in the project resolve from the working folder (as in notebooks). Tested in
  Chrome with Playwright (case 600: open, simulate, plot, 3D). Decided to include it in
  **0.9.0** (phases 1–4 and the opening fix). `simulate(progress=None)`: callback
  `progress(step, n)` after each step (tqdm kept), drives `mo.status.progress_bar` in the
  app (≤ 100 updates). The results viewer is created once per project and `refresh()`ed
  after each run, so plotted variables, frequency, interval and 3D stay and show the new
  values. Pending idea: the editor still loads plotly from esm.sh (the results viewer
  ships it), so the app needs internet for the editor's 3D view.
- **Fix: surface temperatures of openings (branch `fix/opening-surface-temperatures`)**,
  found with the 3D colouring of the results viewer: `Building._store_surfaces_values_()`
  skipped Openings, so their T_s1 stayed 0 and T_s0, q_cd, q_cv1, q_lwt1 (outputs) were
  wrong. Since 0.8.10 it also reached the simulation: the exact exterior long-wave
  correction of a window uses its T_s0 of the previous step (~6 K too cold in case 600).
  Effect: annual heating of the LOAD cases -0.5 to -1.5 %, cooling +0.1 %; LOAD 195/219
  values unchanged, profile points 1213 → 1219 of 1397; other suites unchanged.
- **Paper updated to 0.8.10** (PR #30) and PDF regenerated in the JOSS issue; still
  waiting for the EiC's scope decision.

## Where things stood (2026-10-29)

- **v0.8.10 released (2026-10-29)**: PyPI, GitHub release `v0.8.10`, Zenodo version DOI
  10.5281/zenodo.23762605. All the open ASHRAE 140 items of 0.8.9 were worked on (PRs
  #24–#27, details in the test group sections below): outdoor air volumetric flow (AE),
  case 950 closed, exact exterior long wave radiation (heating level), DX ADP dry coil,
  ISO 13370 periodic ground coefficient (GC45b closed as a limitation). Validation: 2,446
  of 2,740 values inside the reference range (2,379 in 0.8.9).
- **JOSS**: pre-review issue openjournals/joss-reviews#11495 (Managing EiC Matthew
  Feickert, editor/reviewers pending). The EiC asked about the repository history and the
  scope/significance (single contributor, no external interaction); answered on
  2026-10-29. Next: wait for the scope decision; during the review update `paper/paper.md`
  to 0.8.10 (validation figures and numbers, and the Validation sentence that blames the
  constant interior convection for the heating level: the main cause was the exterior long
  wave linearization, fixed in 0.8.10), then `@editorialbot generate pdf`.

- **v0.8.9 released (2026-10-28)**: PyPI, GitHub release `v0.8.9`, Zenodo version DOI
  10.5281/zenodo.23731882. **Paper submitted to JOSS** the same day (subject: Mechanical
  engineering), with version 0.8.9; next: follow the pre-review issue on GitHub
  (openjournals/joss-reviews) and answer the editor/reviewers. Remember to tell L.
  Pérez-Lombard and I. R. Maestre (co-authors).

- **Session of 2026-10-28 (afternoon): minor ASHRAE 140 items** (branch
  `fix/ashrae140-minor`): AE envelope made adiabatic (AIR_SIDE 1164 → 1201/1371); beam
  radiation kept down to 1° solar altitude, was 3° (WEATHER 228 → 241/246, LOAD 176 →
  184/219 values); WD600 albedo 0.2 and the 650/950 vent fan flow confirmed in the Standard;
  `Opening.check()` rejects surfaces other than EXTERIOR/INTERIOR. Details in the test group
  notes below.

- **Session of 2026-10-28: API reference with mkdocstrings** (block 3), plus a fix of
  `Parameter_container.del_parameter()` (it always raised AttributeError). Next in block 3:
  the JOSS paper (draft complete, PR #20); the open items of the ASHRAE 140 validation can be
  interleaved.

## Session of 2026-10-22 (v0.8.8)

- **Session of 2026-10-22: ASHRAE 140 validation automated and v0.8.8 released.** All six
  ASHRAE 140 folders run from `ASHRAE_140/validation/validate.py` (PRs #7–#13, #15), the
  validation is checked in CI (#16), and the fixes it found are in v0.8.8 (#17): published
  to PyPI, GitHub release `v0.8.8`, Zenodo version DOI 10.5281/zenodo.23562791 (concept DOI
  unchanged). Details of each test group and of the open items further below.
- Security note: when publishing to PyPI, never select or paste the API token in the editor
  or the chat (it is sent as context); use `read -s UV_PUBLISH_TOKEN && export
  UV_PUBLISH_TOKEN` in the terminal and revoke any token that was exposed.

## Previous session (2026-10-07, v0.8.7)

- **Session of 2026-10-07: project infrastructure (block 1 of the growth plan below).**
  Merged PRs #3–#6: CI on every push/PR (tests on Python 3.12 and 3.13 + docs build,
  ~2–3 min), `CONTRIBUTING.md`, `CITATION.cff`, issue/PR templates, first GitHub release
  v0.8.7 archived by Zenodo (concept DOI 10.5281/zenodo.23210985), and the docs site now
  built and published by GitHub Actions (`docs/` is no longer committed; Pages source is
  "GitHub Actions", custom domain kept). Working method agreed: one branch + PR per task,
  CI green before merging, the maintainer merges from the GitHub web page.
- Gotcha: `astral-sh/setup-uv` no longer publishes major version tags (`@v10` fails to
  resolve); pin the full version (`@v10.2.0`) when bumping it.

## Automated ASHRAE 140 validation (in progress, started 2026-10-22)

Block 3 below. **Session of 2026-10-22: LOAD_TEST done** (branch
`feat/ashrae140-validation-load`):

- Until now results were copied by hand from each notebook (`to_clipboard()`) into the
  `YourData` sheet of `Std140_*_Results.xlsx`. In those workbooks every reference program
  has a sheet with exactly the same layout as `YourData`, so the reference range of an output
  is the same cells read across the program sheets (located by the `CASE#` header rows).
- The 52 LOAD_TEST case dictionaries moved from the notebooks to
  `ASHRAE_140/LOAD_TEST/cases/case_XXX.json`; the notebooks now `pro.read_json(...)` them
  (single source of truth). Weather file paths stay relative to the suite folder.
- `ASHRAE_140/validation/`: `validate.py` (CLI, simulates in parallel: 52 cases in ~70 s on
  8 cores), `load_test.py` (suite: cases, output extraction, reference reading),
  `report.py` (writes `mkdocs/validation.md` + PNG figures in `mkdocs/img/validation/`).
  Results stored in `ASHRAE_140/validation/results/LOAD_TEST.csv`; `--report-only`
  regenerates the page from it, `--cases 600 900` re-runs only some cases.
- Outputs covered: annual heating/cooling, annual peaks (with date), free-float
  min/avg/max temperatures. The script reproduces the old hand-copied `YourData` values
  (max difference 0.06 °C / 0.4 %).
- Criterion: inside the min–max of the six reference programs (BSIMAC, CSE, DeST,
  EnergyPlus, ESP-r, TRNSYS; BSIMAC has no results for 270–320, 440, 810, 960). This is the
  spread of the programs, not the Standard's formal acceptance criteria.
- **First result: 162/205 outputs inside range.** Annual heating is the weak spot: 20/46
  cases slightly above the maximum (mostly +0.1–1 %, worst 660 at +2.9 %), concentrated in
  the 195–320 series and 610–695. Cooling of 450–470 also above range. Worth investigating
  as a modelling question (systematic heating over-estimate?), separately from this work.
- Cases 610 and 910 read `mets/WD100.tmy3` instead of `725650TY.tmy3`: checked, same Denver
  data hour by hour, so harmless; left as it was.

Next steps, one PR each:

- [x] Remaining LOAD_TEST outputs (branch `feat/ashrae140-validation-load-detail`, stacked
  on the first PR): annual solar radiation, sky temperature, monthly loads of 600/900,
  specific-day hourly outputs, 900FF temperature bins. `load_test.py` now has a map of
  every cell of the output form, `CELLS[(case, output, point)] = (row, col)` (1616 values),
  used to read the references (and reusable to fill `Std140_TF_Output.xlsx`). The page has
  "annual" groups (range chart + tables) and "profile" groups (min–max band + OpenSimula
  line per series). "Inside" now allows 0.1 % of the bound, for the rounding of the reference
  spreadsheets. Result: 1368/1616 values inside range.
- **Findings investigated (2026-10-22):**
  1. *Horizontal hourly solar ≠ GHI* → **bug** in `shadow_calculation = "INTERPOLATION"`
     (`Environment_3D._calculate_shadow_interpolation_table`): the sunny fraction is
     tabulated on a 10° grid (altitude −85…85, azimuth 0…350, not closed at 360) and
     interpolated with **cubic** splines across the 1→0 step where the sun goes behind the
     surface. The overshoot gives fractions of 0.84–1.11 for an unshaded roof (1269 h > 1).
     `INSTANT` gives exactly GHI (1670.17) and is not slower for these cases (7–9 s).
     Impact on loads < 0.2 %. Fix: linear interpolation, sun-behind cells filled with the
     neighbouring front values (or 1), azimuth grid closed at 360.
  2. *Sky temperature* → **not a bug**: same Clark & Allen + Walton model as EnergyPlus and
     it matches EnergyPlus (annual mean −1.99 vs −2.02 °C, min −37.96 vs −37.98; ~1 °C
     hourly). The other programs use models ~10 °C colder on clear days; EnergyPlus is the
     warm edge of the band.
  3. *Jul 14 cooling starts earlier* → **numerical, time step**: lightweight zones respond
     with a ~30 min phase lead at 1 h steps (the implicit hourly value behaves like an
     end-of-hour temperature). 600FF Feb 1 with 15 min steps: −2.5 °C in the morning,
     +2.6 °C in the evening, much closer to the references. Heavy cases (950FF) are fine.
     But 15 min steps *increase* annual loads of lightweight cases (heating +1.5 %, cooling
     +2.5 %), so the heating excess is not a time-step artefact.
- **Done in PR #8 after the investigation:** (1) INTERPOLATION shadow fix (linear,
  sun-behind cells filled, azimuth closed at 360, regression test in `test_Case_610.py`);
  (2) `File_met`: sub-hourly TMY radiation keeps the hour total (linear interpolation
  between hour centres spread 25 % of each hour over its neighbours: hourly value =
  0.75·v(h) + 0.125·(v(h−1) + v(h+1))); hourly simulations unchanged; (3) the validation
  extraction averages every variable over each hour, so it works with any time step.
- **Decision (2026-10-22): the validation stays at 1 h time steps**, the usual practice of
  the other programs. 15 min was tried: 1357/1616 inside (hourly solar and temperatures
  better, annual loads worse, 54/92), not enough of an improvement. Result at 1 h with
  the shadow fix: **1369/1616 inside**.
- **Decision: interior convective coefficients stay constant** (no ΔT-dependent option).
- **Case 195 studied (heating 4.243 vs 3.951–4.217 MWh, EnergyPlus 4.070):** implied
  UA 46.5 W/K vs 43.3–46.2 for the references. Only the cases with interior ε = 0.1 are
  out (195, 200, 215); 210 and 220 (interior ε = 0.9) are inside. Sensitivity of 195
  heating: interior h_cv ×1.5 +6.1 %, ×0.9 −1.9 %, ×0.8 −4.1 % (= EnergyPlus exactly);
  exterior α = 0 +5.3 %; exterior ε = 0 −3.0 %; adiabatic floor −3.6 %; interior ε = 0
  −0.8 %. **Conclusion: the excess comes from the level of the constant interior
  convective coefficients of the case files (walls 2.2, roof 1.8 W/m²K)**; programs with
  ΔT-dependent natural convection (e.g. EnergyPlus TARP) get lower values in winter.
  Accepted as a consequence of the constant coefficients (see the decision above).
- North and east annual incident solar slightly above range also with `INSTANT`
  (483 vs ≤ 477 kWh/m²) → **fixed with the WEATHER_TEST work** (diffuse model on surfaces
  facing away from the sun, see below): north 429, east 1046 kWh/m², both inside.
- [x] HEATING_TEST (branch `feat/ashrae140-validation-heating`): `heating_test.py`, 11
  cases (HE100–HE230) in `HEATING_TEST/cases/*.json` (HE220/HE230 had arithmetic such as
  `6*3600` in their dictionaries, evaluated in the migration). Outputs: furnace load and
  input, fan energy (draft fan = 50 W × burner run fraction F_load/efficiency_degradation,
  computed in the extraction as the notebooks did), mean/max/min zone temperature. Only 3
  reference programs (ESP-r/HOT3000, EnergyPlus, DOE-2.1E), so the ranges are narrow.
  **Result: 32/37 inside**; outside by 0.2–0.7 % (HE220/230 input, HE160/230 fan energy)
  and HE230 minimum temperature 0.14 °C below.
  - Found through HE130 (no load case gave a constant 13 W load and 0.9 GJ input):
    **bug in `Construction._calc_trans_fun_`** — the CTF a, b, c coefficients were cut to
    n_coef − 1 terms, so light constructions with few roots failed the steady state
    (HE130 roof 7.149 vs U 7.140; high-conductance panel 6.59 vs 5.05 W/m²K). Fixed (n_coef
    terms); test in `test_Construction.py`. LOAD_TEST does not change: its high-conductance
    wall is an Opening, whose conduction uses U, not CTF.
- [x] COOLING_TEST (branch `feat/ashrae140-validation-cooling`): two suites, one per
  workbook. `cooling_a_test.py` (CE100–CE200, steady state, February totals/means/max/min,
  10 reference sources incl. 3 analytical solutions) and `cooling_b_test.py` (CE300–CE545:
  annual sums/means, May–Sep sums of CE500/CE510, annual hourly maxima with dates,
  COP2/zone maxima and minima, CE300 weather checks, CE300 June 28 hourly profile, CE500/
  CE530 daily averages; 6 programs). Shared `dx_system.py`: condenser fan = 108 W (a) or
  930 W (b) × run fraction, compressor = power − both fans, COP2 = coil load / (compressor
  + condenser fan) for hours with load. Where the old notebooks disagreed with each other
  the form's definitions were followed (e.g. CE500–CE545 minima of IDB/w/RH over Apr 1 –
  Dec 31, as the form's note says; the hand-copied values used the whole year).
  **Result: a 217/266, b 633/783 inside.** Patterns investigated (2026-10-22):
  - *Series a, zone humidity ratio 5–10 % below the range in the dry-coil cases
    (CE100–CE140)* → **model limitation, not a calculation error.** With no moisture
    sources the zone settles where the coil turns dry, and in `DX_unit` that is where the
    fitted sensible and total capacity curves cross: OpenSimula's equilibrium equals that
    crossing exactly (CE130 6.992 vs 6.989 g/kg). For CE100/110/130/140 the crossing is at
    T_iwb 13.7–14.4 °C, below the catalogue minimum (15 °C): extrapolated polynomials (the
    sensible fit has R² 0.991). The analytical solution and the programs use an
    apparatus-dew-point / bypass-factor coil, ~0.3–0.7 g/kg higher. Loads are not affected
    (the coil is dry in February in all of them). **Done (2026-10-29, branch
    `feat/dx-dry-coil`):** `DX_unit` option `dry_coil_model = "ADP"` (apparatus dew point /
    bypass factor; BF from the nominal point, scaled with the air mass flow; dry when the ADP
    humidity ratio is not below the inlet one, the dry capacity at the wet bulb of the
    dry/wet boundary; wet coil: sensible = max(expression, total × SHR_ADP), so the latent
    goes to 0 continuously). Used in the 34 CE cases. COOLING_A 227 → 259/266, COOLING_B
    423 → 422/519 (profiles 232 → 230). Variants tried: ADP only as dry/wet criterion (wet
    coil from the expressions) 223 and 418, worse; the ADP limit only below the catalogue
    wet bulb (15 °C) makes a jump in the capacity and a case did not converge. **CE430**
    (enthalpy economizer) loses 7 values: the ADP limit lowers the latent removal slightly
    in ~20 % of the spring hours, and the enthalpy economizer amplifies it (moister zone →
    more humid outdoor air): May zone w 10.16 → 10.75 g/kg, annual coil sensible −6 %,
    latent −4 %, w_mean 1 % above the range. Accepted and documented.
  - *CE500–CE545, zone RH 100 %* → **initial conditions.** No infiltration, outdoor air or
    winter gains, so the zone keeps the default initial humidity (Building
    `initial_humidity` 7.3 g/kg) until spring and saturates at ~9 °C in January (CE530:
    47 h). Starting from the end-of-year state (13.3 °C, 5.16 g/kg) the maximum RH is 86 %
    (references 36–96 %). OpenSimula has no warm-up/preconditioning period; possible
    feature: a Project parameter for warm-up days (the Standard's minima for CE500–CE545 are
    taken from April 1 precisely to avoid initialization effects; the maxima are not).
    **Decision: no warm-up; the CE500–CE545 case files use their end-of-year zone humidity
    as `initial_humidity`** (the Standard does not specify it). Effect: the 4 cases at
    100 % RH move inside the range, but the references evidently started moister (their
    maximum humidity ratio and CE540 annual latent load include removing initial moisture),
    so CE530/540/545 maximum w, CE540 coil latent and CE530 mean RH move below (632/783,
    was 633). Known limitation: the dry-coil criterion of `DX_unit` (decision, not to change).
  - *CE500–CE545, consumption, fan energy and coil loads above range* → **error in the
    case files' internal gains schedule, fixed.** Checked against Tables 9-22 (CE500) and
    9-23 (CE510) of the Standard: the period changes were one day early (now 11/03, 11/04,
    12/04, 21/04, 12/10, 19/10, 06/11, i.e. "Jan 1 thru Mar 10", "Mar 11 thru Apr 10",
    "Apr 11", "Apr 12 thru Apr 20", "Apr 21 thru Oct 11", "Oct 12 thru Oct 18", "Oct 19 thru
    Nov 05", "Nov 06 thru Dec 31") and three transition periods were 2 h too long (now
    9:00–16:00, 8:00–17:00 and 8:00–14:00). Values were right. CE500 annual latent gains
    18.596 → 18.236 MWh (references' coil latent 18.08–18.35). Series b: 633 → 658/783;
    CE500–CE545 coil loads 9/9 inside. Still outside: fan energy and total consumption of
    CE520/522/525/540 (the set point variants), CE540 coil latent (initial humidity) and the
    minimum IDB (below).
  - *CE300–CE440 schedules* checked against Tables 9-20 (CE310), 9-21 (CE360) and the CE320
    infiltration schedule: hours and values right, but every period change one day early
    too (now 11/03, 11/04, 12/04, 21/04, 13/10, 19/10, 06/11 — note "Apr 21 thru Oct 12"
    here vs "Oct 11" in CE500 — and 21/04, 13/10 for the infiltration/ventilation/
    thermostat schedules of CE320–CE350; those of CE330–CE350 assumed to follow the same
    dates, their tables not checked). Effect < 0.25 %; series b 658 → 660/783.
  - *LOAD_TEST night ventilation, fixed:* the Standard (Section 7.2.2.1.5.1) has the vent fan
    ON 18:00–07:00 (hours 19–7) and OFF 07:00–18:00; cases 650 and 950 had it off
    08:00–19:00, one hour late (650FF/950FF were right; 650FF's odd 7.083 h first step set
    to 7 h). 650 annual cooling 4.883 → 4.786 MWh (inside), 950 0.834 → 0.786 (range
    0.586–0.707, still above: with 950FF maximum temperature also slightly above, the
    heavy-mass night-ventilated zone is worth a look).
    **Studied 2026-10-28:** the vent flow is right — Table 7-16: 1700 m³/h = 13.12 ach for
    programs that correct the mass flow for altitude (OpenSimula does, with the weather
    file altitude; 1409 m³/h only for sea-level programs). Interior convection ×2 lowers
    950 cooling only 0.771 → 0.744 MWh. **Closed 2026-10-29: the night ventilation is
    right.** Its effect, 950 − 900 annual cooling, is −1.801 MWh in OpenSimula vs −1.626 to
    −2.128 (mean −1.833) in the references (650 − 600: −1.168 vs −1.147 to −1.259). The
    excess of 950 (+0.137 MWh over the references' mean) is the base cooling level of 900
    (+0.105 MWh, inside its range), which is out of range only because 950's cooling is
    small. See the systematic heating level below.
  - *Systematic heating level, found and mostly fixed 2026-10-29 (branch
    `fix/case-950-night-vent`):* annual heating was above the references' mean in almost
    every case, typically +4 to +8 % (600 +6.1 %, 900 +8.4 %, 910 +11 %). Cause: the
    exterior long wave exchange with sky and ground (`Building_surface` and `Opening`) was
    linearized with H_RD = 4σ·293³ = 5.7 W/m²K, which in winter (surface and sky at −20…0 °C,
    4σT³ ≈ 4.1–4.6) overestimates the loss to the sky by 25–35 %. The building matrices keep
    the linearized term and the difference with the exact εσ(F_sky·T_sky⁴ + (1−F_sky)·T_ext⁴
    − T_s⁴) is added explicitly to f_0, with the surface temperature of the previous time
    step (`Building_surface.long_wave_correction`). Interior exchange stays linearized at
    20 °C. LOAD 184 → 195/219, profile points 1171 → 1213/1397; the other suites unchanged.
    Heating now +2 to +4 % over the mean (600 +2.9 %, 900 +1.9 %); the remaining part is not
    the film coefficients (195, conduction only and ε = 0.1, is +3.3 % but inside its
    range; the exterior film is < 4 % of the wall resistance). Possible feature: exterior
    convection depending on wind speed. Regression values: 600FF mean +0.9 %, min −7 %;
    610 heating −3 %; DX tests −2 to −3.4 %; fan coil heating −9 % (small values).
  - *CE520–CE540 fan energy and consumption 0.2–2 % above* (coil loads inside): longer run
    time from a lower total capacity, because the zone humidity is below the range in those
    cases (CE540 −34 % → fans +2.1 %, CE525 −6 % → +0.2 %). Consequence of the known
    dry-coil limitation of `DX_unit` and the initial humidity, not a separate error. The 640/940 thermostat (linear
    10 → 20 °C from 07:00 to 08:00, step down at 23:00, Figures 7-7/7-8) is right.
  - *CE500–CE545, minimum IDB 7.48 °C vs 7.94–8.94* (Dec 20): quasi-adiabatic envelope
    (1 m of k = 0.003) and air-only capacity, ~5-day time constant, so the zone follows the
    outdoor/sky conditions; the references themselves spread 1 K. Not investigated further.
  - CE430: annual coil loads ~3 % below the hand-copied values (model changes since v0.5).
- **Case notebooks archived** in `<TEST>/old_notebooks/` for every automated folder (LOAD,
  HEATING, COOLING): their first cell changes to the test folder so they still run. Do the
  same when automating the next folders.
- [x] GROUND_TEST (branch `feat/ashrae140-validation-ground`): `ground_test.py`, 14 cases
  (steady-state GC30b/30c/60b/65b; harmonic GC40b–GC80c, 2-year runs, final year). Outputs:
  floor conduction and zone load, annual sums/mean, hourly maxima with dates, minimum ODB,
  GC40b/GC40c hourly floor conduction (only from the 5 sheets whose hourly columns follow
  the output form). Extraction reproduces the hand-copied values (≤ 1e-5). **55/68 values
  and 7393/17520 hourly points inside.** GC45c's project was named "Case GC40c" (fixed).
  - Found: `Building` radiosity matrix (I − F·ρ) is singular when no surface absorbs (GC
    cases have solar absorptance and emissivity 0); GC50b raised "Singular matrix". Fixed
    with a pseudo-inverse fallback.
  - **Deep-ground boundary added (Standard, Table 8-1: depth E = 15 m at 10 °C, far field
    15 m adiabatic):** the case files had no deep boundary (semi-infinite ground in the ISO
    13370 model) except the water-table cases GC55b (2 m) and GC55c (5 m); now
    `groundwater_depth` = 15 in the other 12. GC50b (80 × 80 m) annual floor conduction
    205 699 → 302 865 kWh (range 277 923–324 257, inside; its peak now 1.7 % above); the
    rest +0.7 %; GC45b (36 × 4 m) unchanged, ~1 % below. **Periodic part fixed (2026-10-29, branch
    `fix/ground-periodic`):** the amplitude of the equivalent exterior ground temperature used
    λ/√((0.457·B' + d_t)² + δ²), almost independent of the slab shape; now the ISO 13370
    periodic external coefficient H_pe = 0.37·P·λ·ln(δ/d_t + 1), proportional to the
    perimeter (per m²: GC40b 0.47 → 0.55, GC45b 0.58 → 0.91, GC50b 0.15 → 0.08 W/m²K). GROUND
    71 → 78/82 values, hourly points 7888 → 8760/17520, none lost: GC45b peak −8 % → −1.2 %
    below the range, GC50b/GC70b/GC80b/GC55c peaks inside. **Remaining, closed as a model
    limitation:** the 4 GC45b values (annual and peak floor/zone conduction) ~1 % below the
    lowest reference, from the steady-state ISO 13370 transmittance of a narrow slab
    (B' = 3.6 m). Values 55 → 57/68, hourly
    7393 → 7888/17520. Rest of Table 8-1 / Section 8.2.1 checked in the case files (soil,
    adiabatic massless walls, volume, initial 10 °C, set points, h = 100, slab 0.01 m, wall
    0.24 m). Sections 8.2.1.2–8.2.1.9 (b-series) checked too: GC45b 36 × 4 m, GC50b
    80 × 80 m, GC55b E = 2 m, GC60b h_int 7.95, GC65b h_int 7.95 / h_ext 11.95 + GC65b.TM2,
    GC70b the same on GC40b + GC70b.TM2, GC80b k = 0.5 — all as in the case files.
    Simulation duration (≤ 0.1 % change between the last two years): steady-state cases are
    steady from year 1, harmonic cases from year 2 (the ISO 13370 model has only 0.5 m of
    dynamic ground), so 1 and 2 years are enough. c-series (8.2.3) checked too: GC30c
    interior combined 7.95, exterior surface at T_o = 10 °C via h_ext 10000 (≥ 5000 allowed)
    and GC30a.TM2; GC40c GC40a.TM2; GC45c 36 × 4 m; GC55c E = 5 m; GC80c k = 0.85 — all as
    in the case files. E for the c series is inherited from GC30b (15 m, Table 8-9 does not
    change it). Model limitation: the c-series far-field distance F = 8 m (and F in general)
    cannot be set in the ISO 13370 ground model. Added outputs: steady-state zone
    temperature and hours at the minimum outdoor temperature (71/82 values inside).
  - GC40b hourly floor conduction ~5 % below a narrow band (3 programs) all year; the shape
    and amplitude match.
- [x] AIR_SIDE_HVAC_TEST (branch `feat/ashrae140-validation-airside`): `airside_test.py`, 24
  steady-state cases (fan coil AE100, single zone AE200, CV terminal reheat AE300, VAV
  AE400), last hour: zone/coil loads, coil outlet RH, reheat, and the psychrometric state
  (T, w, v, h, m) at every location. Both workbooks share the layout: AE100/200 read from
  FCSZ, AE300/400 from CVVV (8 programs incl. LCEM for 100/200). The programs report loads
  with different signs (EnergyPlus/LCEM/DOE-2.2 negative heating in places), so loads are
  compared as magnitudes. **1122/1371 values inside.**
  - Found and fixed: `HVAC_SZW_system` never computed the coil capacity with
    `water_source` "UNKNOWN" (UnboundLocalError as soon as it heated or cooled); `Space`
    reported stale uncontrolled-system loads after a VAV system switched to a controlled
    flow (AE403 zone 1: 5.1 kW instead of 1.45 kW). AE400 summary values 59 → 79/91.
  - `test_editor_schema` now validates the 135 case JSON files against the editor schema.
  - **Multizone humidity convergence — fixed (branch `fix/humidity-convergence`).** Two
    problems in `Iterative_process` (used by `Space` for T and w and by `HVAC_water_system`):
    (1) convergence tested the relaxed step |x_k − x_k−1| = λ·residual, so with λ down to
    0.1 it stopped with residuals up to 10 × tol; now it tests the fixed-point residual
    |proposed − x|; (2) λ was reduced by 0.8 every iteration whether or not the iteration
    oscillated (the adaptive check was commented out), so well-behaved loops crawled; now λ
    is reduced only when the residual changes sign or grows, and recovered while it
    contracts (the "grows" guard is needed: CE200 diverged to 696 °C without it). Space
    `convergence_Dw` default 0.1 → 0.01 g/kg. AE303 zone 1 latent 0.738 → 0.5905 kW
    (references 0.586–0.590); CE200 coil latent 1221 (range 1210–1222). Runtime about the
    same overall (CE150 30 → 15 iterations per step, two-zone AE cases 6–8 → 10–12).
    Validation: COOLING_A 217 → 227, AIR_SIDE 1122 → 1164, COOLING_B 660 → 655 (5 values at
    the range edges moved < 0.6 %), the rest unchanged.
  - **AE101/201/301/401 zone heating load 3 % above — fixed (2026-10-28):** the adiabatic
    envelope of the 24 AE cases was 1 m of insulation with k = 0.01 (U ≈ 0.01 W/m²K × 171.6
    m², ~0.09 kW lost at −29 °C); now k = 1e-6 and the zone loads equal the imposed gains
    (2.931 kW). AIR_SIDE 1164 → 1201/1371.
  - Remaining in AE101/AE201: outdoor air mass flow 0.110 vs 0.113–0.120 kg/s, heating coil
    load 1.3 % below. **Checked in the Standard (2026-10-28):** supply 600 cfm at the supply
    fan inlet conditions (as OpenSimula does) but outdoor air 200 cfm at the *exhaust fan
    inlet* conditions (return air, zone temperature), while `outdoor_air_fraction` of
    `HVAC_SZW_system`/`HVAC_MZW_system` is a fraction of the supply *mass* flow. So the
    outdoor air is short when heating (warm supply) and slightly high when cooling (AE104
    0.1 % above). **Done (2026-10-29, branch `feat/outdoor-air-flow`):** new parameter
    `outdoor_air_flow` (m³/s at zone air conditions, the air exhausted from the zone) in
    `HVAC_SZW_system` and CV `HVAC_MZW_system`, an alternative to `outdoor_air_fraction`
    (`check()` rejects both, and `outdoor_air_flow` in VAV); the economizer can still take
    the fraction up to 1. The return air flow is now the zone mass balance, supply − minimum
    outdoor air (it was the return fan volume × zone density, or 0 in the extraction with
    100 % outdoor air). AE100–AE300 cases use 200 cfm (0.09439) and 500 cfm (0.23597).
    AIR_SIDE 1201 → 1219/1371: outdoor air flows of AE101–AE306 and the return flows of the
    economizer cases now inside; a few tight mixed-air humidity/enthalpy values of AE303/305
    moved just outside. VAV (AE400) unchanged: its outdoor air (supply − return volumes at
    different densities) is still ~1.5 % high in AE403–AE406, but computing it as a mass
    balance at zone conditions lost more values than it gained (1188), so left as is.
- [x] WEATHER_TEST (branch `feat/ashrae140-validation-weather`): `weather_test.py`, six cases
  WD100–WD600 (same building, different weather file, 10 min steps), annual averages of the
  weather variables and of total/beam/diffuse radiation on the horizontal and nine surfaces,
  vs eight programs and the weather file itself. **228/246 inside.**
  - Found and fixed: Hay-Davies, Reindl and Perez in `File_met.solar_diffuse_rad` fell back
    to the isotropic model whenever the sun was behind the surface (or no beam), giving
    shaded faces the circumsolar sky: WD100 north diffuse 32.5 vs 21.8–28.9 W/m². Now the
    circumsolar term uses cos θ clipped at 0 and the sky keeps its anisotropy weighting;
    Perez overcast bin includes ε = 1. Perez is the default: on a cloudy day OpenSimula now
    matches EnergyPlus/ESP-r/TRNSYS (BSIMAC/CSE/DeST behave isotropically). LOAD_TEST
    1369 → 1344 (north/east incident now inside, but less solar adds to the known heating
    excess); other suites unchanged.
  - **WD600 ground albedo 0.2**, first inferred from the reference results (vertical diffuse
    ~19 W/m² higher than WD100 = 0.2 × 190 × 0.5), **confirmed in the Standard** (2026-10-28).
  - **Vertical beam 0.2–2 % below the range — fixed (2026-10-28):** `File_met` moved the
    beam to the diffuse below 3° of solar altitude, losing the low-sun beam on vertical
    surfaces. Now `MIN_SUN_ALTITUDE = 1` (0.5° put WD200 east beam 1.3 % above: the
    horizontal beam / sin(altitude) amplifies the file's errors near the horizon). WEATHER
    228 → 241/246, LOAD 176 → 184/219; regression tests updated (annual loads −0.9 to
    +0.5 %). Better alternative if needed: use the DNI of TMY files directly instead of
    (GHI − DHI) / sin(altitude).
  - Remaining: sky temperature 0.01–0.02 °C above in WD300/WD500; WD300 south total and
    WD200/WD500 east/north beam within 2 % of the bounds.
- **All six ASHRAE 140 folders are automated** (LOAD, HEATING, COOLING a/b, GROUND,
  AIR_SIDE, WEATHER); all case notebooks archived in `<TEST>/old_notebooks/`.
- [x] CI (branch `ci/ashrae140-validation`): `validate.py --check` compares with the stored
  CSVs (fails beyond 0.1 % relative + 1e-4 absolute) and `--quick` runs `QUICK_CASES` (18
  representative cases, ~2 min). `.github/workflows/validation.yml`: quick on pull requests
  touching src/ASHRAE_140/mets/dependencies, full on merges into `main`, releases and manual
  runs. Workflow for intended changes documented in `CONTRIBUTING.md`.
- [ ] Optionally fill `Std140_TF_Output.xlsx` (the plain output form) from the CSV, to paste
  into the Standard's workbook. Do not write into `Std140_*_Results.xlsx` with openpyxl: it
  drops the charts.

- The `pro.editor()` Jupyter widget's `_esm` module is now fully bundled (Ajv included), so
  it loads in VS Code notebooks as well as JupyterLab (was issue #1, fixed on
  `fix/editor-vscode-ajv-import`, merged in PR #2).
- 3D visualization is now Plotly-only: `vedo`/VTK have been fully removed (dependency,
  `get_vedo_mesh()`/`get_vedo_meshes()`, the desktop `Plotter` window). `Project.show_3D()`
  only shows and returns nothing; `Project.plotly_figure_3D()` returns the figure to compose
  or save instead. Removing `vedo` also uninstalled `matplotlib`, which was only a transitive
  dependency but is imported directly by `Environment_3D.show_sunny_fraction()` — it is now
  declared explicitly in `pyproject.toml`. Worth remembering if another dependency is ever
  dropped: check `uv sync`'s uninstall list for anything the code still imports directly.
- `README.md` was rewritten for GitHub/PyPI (badges, quick example, component overview).

## Known follow-ups

Concrete, verified items — not ideas, things already identified as needing attention:

- **`HVAC_DX_system.py:14`** — the `spaces` parameter's comment notes it should eventually
  also accept `Air_distribution` and `Energy_load` component types, neither of which exists
  yet in the codebase.

## Planned: several generators and pumps in a water loop (discussed 2026-11-18)

Today an `HVAC_water_system` is one loop with one generator (`water_thermal_generator`, only
`Chiller_heat_pump`) and one pump (`pump`); there is no `Boiler` yet. Goal: more than one
generator per loop, more than one pump, and the usual primary/secondary separation.

- **Name decided: `HVAC_water_generator`** — a simulated component (variables, `HVAC_` prefix
  like the other systems) that uses an equipment component as the manufacturer's data and
  is what connects to `HVAC_water_system`.
- Equipment (data only, like `DX_unit`): `Chiller_heat_pump` and a new **`Boiler`** (nominal
  capacity, efficiency vs part load and return temperature for condensing boilers, fuel type
  for primary energy / CO₂ later).
- `HVAC_water_generator`: `equipment` (Chiller_heat_pump or Boiler),
  `number_of_units`, its own primary `pump`, availability (`system_on_off` expression).
  Priority = order in the plant's `generators` list; heating/cooling ability = type of
  equipment (decisions 1-2 below). Variables: decision 9.
- `HVAC_water_system`: `generators` (component list) instead of
  `water_thermal_generator`; `pumps` (list) that move the water of the coils connected
  directly to the plant, as its own secondary (replaces `pump` and `design_water_flow`;
  same staging as a circuit's pumps); loop volume as the buffer tank / header; setpoints;
  sequencing strategy.
- **Design closed (2026-11-18)** — no decisions left for the implementation:
  1. **Mode:** one mode at a time per plant (two-pipe), from the load or a schedule as
     today; only the generators able to serve it run (a `Boiler` only heats; a
     `Chiller_heat_pump` according to its existing `chiller_type`). Heating and cooling at
     the same time: two plants (four-pipe).
  2. **Sequencing:** `PRIORITY` by the order of the `generators` list (the next one starts
     when the previous one is at 100 %); `EQUAL_LOAD` as an option (same fraction for all
     those that can run). `number_of_units` = N identical units sequenced the same way. No
     minimum part load: cycling is in the part-load degradation curves.
  3. **Setpoint:** each generator tries to give the plant setpoint at its own outlet; the
     header temperature results from the mixing (bypass when secondary flow > primary).
  4. **Flows:** coils report their water flow too, `add_coil_load(Q, flow)` instead of
     `add_coil_load(Q)` (changes `HVAC_SZW_system`, `HVAC_MZW_system` and reheat once). First
     version: constant-flow secondary pumps (three-way valves); variable flow later.
  5. **Pumps:** one primary pump per generator (`HVAC_water_generator.pump`, constant flow =
     generator nominal, only while it runs; a stopped generator lets no water through).
     `pumps` list per `HVAC_water_circuit`, in parallel, staged by flow (next one when the
     previous exceeds its nominal flow). No standby pumps. Heat of the pumps to the water
     (`power_to_heat_fraction`) in the circuit where each pump is. `Pump` already allows VSD
     through `power_expression(F_water)`.
  6. **Circuit:** optional `supply_setpoint` (expression) with a mixing valve that can only
     lower the temperature in heating / raise it in cooling; without it, or if the header
     cannot reach it, the header temperature. Own `system_on_off`. Optional `water_volume`
     and `Q_loss` (default 0). Mode inherited from the plant.
  7. **Compatibility broken in 0.10:** `water_thermal_generator`, `pump` and
     `design_water_flow` of `HVAC_water_system` are removed; example 07, the test notebooks
     (`jupyter_test/test_HVAC_FAN-COIL_water_system.ipynb`, `test_process_water_system`) and
     the docs are migrated (few cases use water systems; ASHRAE 140 none).
  8. **`Boiler`:** nominal capacity and efficiency on the lower heating value (LHV);
     efficiency expression of `F_load` and return water temperature `T_wi` (condensing
     boilers); `fuel` (natural gas, oil, biomass, electricity…) informative for now, for
     primary energy / CO₂ later; maximum supply temperature. Same expression pattern as
     `DX_unit` and `Chiller_heat_pump`.
  9. **Outputs:** per `HVAC_water_generator` (load, electric or fuel power, efficiency, part
     load, flow, supply/return temperatures, pump power); per `HVAC_water_circuit` (load,
     flow, supply/return, pump power, mixing flow); totals in `HVAC_water_system` (load,
     total electric power of generators and pumps, total fuel power, header temperature).
- **Secondary circuits decided: new `HVAC_water_circuit`** (option A, 2026-11-18), so that a
  plant can feed several secondaries, each with its own air systems and pumps:
  - `HVAC_water_system` becomes the plant: generators, header / buffer tank, production
    setpoints, sequencing.
  - `HVAC_water_circuit`: `water_system` (the plant it hangs from), `pumps` (list, in
    parallel, staged by flow), flow control (constant / variable with VSD), supply
    temperature (that of the header, or its own setpoint with a mixing valve, e.g. radiators
    at 70 °C and radiant floor at 35 °C from the same boiler), volume and losses. Variables:
    flow, supply/return temperatures, load, pump power, bypass / mixing flow.
  - Towards the coils a circuit offers what the plant offers today
    (`get_*_coil_inlet_T()`, `add_coil_load()`); towards the plant it behaves as one more
    coil (takes water from the header, returns its load). Order: air systems → circuits →
    plant; the existing iteration loop makes them converge.
  - Air systems (`HVAC_SZW_system`, `HVAC_MZW_system`) refer with `heating_water_system` /
    `cooling_water_system` to a circuit or, as today, directly to the plant: without
    circuits nothing changes (example 07 stays as it is).
  - Rejected: a recursive `HVAC_water_system` fed by another one (two very different roles in
    one component, harder to teach).
- Four-pipe installations: two `HVAC_water_system` (hot and cold). A polyvalent heat pump
  serving both loops at once is a later step.
- Order of work: `Boiler` → `HVAC_water_generator` with one generator → several generators
  and sequencing → primary/secondary (header) → `HVAC_water_circuit` secondaries → variable
  secondary flow.
- **B1 done (PR #49, merged)**: `Boiler` (data only): fuel, nominal capacity and efficiency
  (LHV), `efficiency_expression` of `T_wi`, `T_wo`, `F_water`, `F_load`, maximum supply
  temperature, auxiliary power. Own interface (`get_heating_load(T_wo, T_wi, flow, Q)`,
  `get_fuel_power`, `get_auxiliary_power`): the outdoor air does not matter to a boiler.
- **B2 done (branch `feat/water-generator`)**, split as agreed 2026-11-19:
  - `HVAC_water_generator` (equipment Chiller_heat_pump or Boiler, `pump`, `system_on_off`;
    variables Q, F_load, power, fuel_power, efficiency, water_flow, T_wi, T_wo, pump_power).
    `HVAC_water_system.generators` (one only until B3) replaces `water_thermal_generator`;
    `pump` and `design_water_flow` gone: no header yet, so the loop is moved by the pump of
    the generator at the nominal flow of its equipment. The plant's `pumps` list comes with
    the header (B4). `pump_operation` stays in the plant.
  - `add_coil_load(Q, flow)`: SZW and MZW send design flow × F_load; stored as
    `coils_water_flow`, not used yet (B4/B6).
  - Results bit-identical (example 07, the water tests) except `generator_part_load`: it
    kept the previous step's value when the generator gave nothing, and was 1 at full load
    while the power was computed with the part load at the actual supply temperature.
  - **`HVAC_MZW_system` was not connected to its water systems** (parameters and docs said
    so, the code used the fixed inlet temperatures and sent no load): now connected, coils
    and reheat (own `reheat_water_temp`). AIR_SIDE validation: 0 changed. Test: four-pipe
    VAV with reheat, boiler plant and chiller plant, two `Load_space` zones
    (`test/mzw_four_pipe.json`, also `~/Desktop/opensimula_0.10/B2_mzw_four_pipe.json`).
  - Fix (own commit): VAV outdoor air fraction from the flow balance limited to 0-1 (with
    return = supply it was -1e-16 and the mixed air humidity negative → psychrolib error).
  - Migrated: example 07, `test_HVAC_FAN_COIL_water_system.py`,
    `test_HVAC_water_system_process.py`, the two `jupyter_test` water notebooks.
- **B3 done (branch `feat/water-sequencing`)**: several generators per plant, in parallel
  (no header yet): loop flow = sum of the nominal flows of the available generators, each
  moved by its pump; one not available lets no water through. `sequencing` PRIORITY (list
  order, next at full load of the previous) / EQUAL_LOAD (same part load); only those able
  to serve the mode run (boiler only heats). `number_of_units` in the generator: capacity
  and flow × N, units share the load with the plant's sequencing, power per unit at its own
  part load; variable `units_on`. Plant: `generator_fuel_power`; `generator_efficiency` of
  several = heat / (electric + fuel). One generator, one unit: bit-identical to B2. Tests
  `test_HVAC_water_sequencing.py` (exact shares with a constant process load). Test
  project `~/Desktop/opensimula_0.10/B3_heat_pump_and_boiler.json` (4 kW heat pump first,
  boiler backup: HP 591 kWh / boiler 397 kWh heating; HP undersized in cooling, 433 h >
  25.5 °C).
- **B4 done (branch `feat/water-header`)**: header (primary / secondary) when the plant has
  secondary `pumps` (optional: without them B3 behaviour, bit-identical). Ideal decoupler,
  water lumped at the secondary supply (`total_water_volume`); secondary pumps at nominal
  flow (constant, three-way valves; staging and variable flow → 0.11), primary pump of
  each generator only while it runs; bypass both ways; each generator aims at the setpoint
  at its outlet (decision 3): with primary < secondary the supply is below the setpoint.
  Bugs found and fixed: heat of the secondary pumps counted twice (water overheating,
  caught by checking the energy balance), and `get_pump_heat(0)` = nominal power (own
  commit). Small balance residuals (≤ 66 W in 13 of 8760 h, also ≤ 49 W without header)
  from the relaxed last iteration. Test project
  `~/Desktop/opensimula_0.10/B4_header_two_boilers.json` (primary 0.5 > secondary 0.3:
  boiler inlet ≈ supply, little condensing). **Plant variables renamed** (agreed
  2026-11-19): `T_supply`, `T_return`, `T_generators_out`, `T_generators_in`, `T_mean`,
  `primary_flow`, `secondary_flow`, `bypass_flow`, `coils_flow`, `Q_generators`,
  `generators_power`, `generators_fuel_power`, `pumps_power`, `secondary_pumps_power`, new
  `electric_power`; `water_flow`, `generator_efficiency`, `generator_part_load` removed
  (per generator). Tests, notebooks (run fully) and docs updated.
- **B5 done (branch `feat/water-circuit`)**: `HVAC_water_circuit` (water_system, pumps at
  nominal flow, system_on_off, pump_operation, heating/cooling_supply_setpoint mixing valve
  = max / min supply whatever the plant mode (first version depended on the mode: the
  supply jumped when the plant left standby and the stored energy of the circuit made the
  plant mode oscillate), Q_loss, water_volume). Towards the plant one more coil
  (`add_coil_load(Q_plant, plant_flow)`), towards the coils the plant interface
  (`get_*_coil_inlet_T`, `add_coil_load`, `on_off` property: circuit and plant on). SZW
  and MZW accept a circuit in their water system parameters. Order: air systems →
  circuits → generators → plant. Tests `test_HVAC_water_circuit.py` (exact mixing with a
  loss as load, two circuits at 35 / 55 °C, off, volume, fan coil of 07 on a circuit at
  40 °C). Test project `~/Desktop/opensimula_0.10/B5_two_circuits.json` (plant 60 °C, AHU
  circuit 60 °C, reheat circuit 40 °C: takes 0.003 of its 0.2 dm³/s from the plant).
- **Follow-ups for 0.10 done (branch `fix/water-coil-mode`)**:
  - Coils ask the plant `can_heat()` / `can_cool()` (off, or SCHEDULE_CONTROL in the
    opposite mode: no), besides the water temperature; circuits delegate to their plant.
    Fan coil test (SCHEDULE_CONTROL): −71 kWh of cooling that had no generation; example
    07 and the rest unchanged.
  - Generator capacity at the actual water temperature when it cannot reach the setpoint:
    bisection of T = T_pre + (capacity(T) + rest) / C between the setpoint and the free
    temperature (a fixed point diverged with little water: dcap/dT 253 W/K > C 116 W/K);
    the same in the header path, with the outlet / inlet temperatures from the mixing.
    Boilers (capacity independent of T) bit-identical. High load test: the water warms up
    to 50.5 °C instead of 69.5 °C (the chiller gives more with warmer water), annual
    generation −0.004 %; example 07: 85 steps at full load, annual +0.01 %.
- **Example 09 Water plant (PR #56, merged)** and **docs for 0.10 (branch
  `docs/water-plants-guide`)**: user guide section "HVAC systems and water plants" (diagram
  of the references, plant, generators, header, circuits, example code) and a new page
  `mkdocs/release_notes.md` (0.10: new, fixes that change results, upgrading from 0.9 with
  the JSON migration and the table of renamed variables). Left for the release: full
  validation, version 0.10.0, CITATION, PyPI (the user), GitHub release, Zenodo.
- **Scope of 0.10 (agreed 2026-11-19)**: B3, B4, B5 + the coil mode check and the
  generator capacity at the actual temperature; B6 (variable secondary flow, pump staging)
  moved to 0.11.
- **Follow-ups found in B2** (the first two done, see above):
  - `File_data` with `file_step` "SIMULATION" ignores the dates: a simulation that does not
    start on 1 January reads the file from its first row. Use "OWN" with `initial_time`.

## Planned: `Load_space`, air systems against load records (discussed 2026-11-19)

Goal: simulate an HVAC installation without the building, from precalculated load records
(a column of `File_data`, a schedule, a `Calculator`…). A new component **`Load_space`**
takes the place of a `Space` in `HVAC_DX_system`, `HVAC_SZW_system`, `HVAC_MZW_system` and
`HVAC_perfect_system`. Fully backwards compatible: nothing existing changes behaviour.

- **What the systems use of a space** (checked 2026-11-19): `variable("temperature")`,
  `variable("abs_humidity")`, `get_thermal_equation(bool)` → `(K, F)` with
  `K·T = F + Q_sys`, `get_humidity_equation(bool)` (perfect system), `set_control_system`,
  `add_uncontrol_system` / `del_uncontrol_system` (MZW). Nothing of the building. A
  `Load_space` offering these works with the four systems unchanged.
- **Base class `Thermal_zone`** (decided): taken out of `Space`, holds the control /
  uncontrolled systems bookkeeping, `get_thermal_equation`, `get_humidity_equation`,
  `get_Q_required`, `get_M_required`, the iteration with `Iterative_process` and the
  `system_*_heat` outputs. `Space` provides its `K_F` from the building, `Load_space` its own.
  Own commit, `validate.py --check` must give 0 changes.
- **Allowed types**: `["Space"]` → `["Space", "Load_space"]` in the four systems (the check
  is by class name, `type(comp).__name__`, inheritance is not enough). Parameter names
  unchanged. `Load_space` goes after `Space` in `DEFAULT_COMPONENTS_ORDER` (projects with
  their own `simulation_order` get it first, also valid).
- **Inputs**: `input_variables` + expressions `sensible_load` (W, positive heating, as
  `system_sensible_heat`) and `latent_load` (W), as `Space_type` / `Calculator`.
  `reference_temperature` (expression, default `"24"`) and `reference_humidity` (relative
  humidity at `T_ref`, expression, default `"50"` %): the conditions the record was
  calculated at. Records should be calculated at a fixed setpoint: one from a system with a
  dead band is 0 inside it while the temperature floats (document it).
- **Model (decided): two nodes, air and mass**, in deviations `θ = T − T_ref`, imbalance
  `ΔQ = Q_sys − Q_load`, implicit Euler (any time step, unconditionally stable):
  `C_a·dθ_a/dt = ΔQ − H_ao·θ_a − H_am·(θ_a − θ_m)`, `C_m·dθ_m/dt = H_am·(θ_a − θ_m) − H_mo·θ_m`.
  The mass node is eliminated → same `K·T = F + Q_sys` form. The record already has the
  building's dynamics at constant temperature; the model only says how far and how fast
  the zone leaves `T_ref` when the system does not match the load (what ASHRAE's space air
  transfer function does; at 1 h it has the same g₀, g₁, p₁ structure).
- **Parameters, all with defaults** (per floor area):
  - `floor_area` 100 m², `height` 2.7 m (air volume);
  - `construction` `VERY_LIGHT` / `LIGHT` / `MEDIUM` (default) / `HEAVY` / `VERY_HEAVY` →
    `C_m` and `A_m` from ISO 13790 table 12 (80/110/165/260/370 kJ/(m²·K); A_m 2.5–3.5 ×
    floor; **check the values before fixing them**), `H_am = 9.1·A_m`; `C_m`, `H_am`
    overridable;
  - `C_a` = air + 10 kJ/(m²·K) of furniture;
  - `envelope_conductance` 1.0 W/(m²·K) of floor, half to the air node (`H_ao`, windows),
    half to the mass (`H_mo`, opaque).
  - Hand estimate (100 m², MEDIUM, 1 kW unmet): ~0.4 K in minutes, ~0.7 K in the first
    hour, then slowly with the mass (a day or more). Simulate and adjust the defaults.
- **Infiltration (decided)**: `load_infiltration` (ach, expression, the one the record was
  calculated with) and `infiltration` (ach, expression, the one simulated), both default
  `"0.5"`. The record's infiltration is taken out at the reference conditions
  (`Q_load − ρ·cp·V·n_load/3600·(T_ref − T_ext)`, `L_load − λ·ρ·V·n_load/3600·(w_ref − w_ext)`)
  and the real one added at the zone's actual T and w (term in the air node and in the
  humidity balance). Exact (linear in T and w); with `n = n_load` and the setpoint held the
  load is the record's. Same infiltration for sensible and latent; renews the air while the
  system is off; allows `"0.5 * (1 - f)"`. Assumes the record's infiltration enters at
  outdoor conditions, without heat recovery (document it).
- **Outputs**: `temperature`, `abs_humidity`, `rel_humidity`, `sensible_load`, `latent_load`
  (evaluated), `system_sensible_heat`, `system_latent_heat`, `unmet_sensible_heat`.
- A `File_met` is still needed (equipment curves, outdoor air, infiltration).
- **Validation**: example 05 at a fixed setpoint → its load into a `Load_space` (LIGHT) with
  the same perfect system must give `T = T_ref`, unmet 0; with the DX of example 06, hours
  out of setpoint and energy close to the full building; and infiltration `0.5` → `"0.5 *
  (1 - f)"` compared with the building simulated directly that way.
- Editor: a family in the graph (with the spaces). Docs: component page and a gallery
  example (DX against the loads of example 05 read from a `File_data`).
- **Development plan of 0.10 (2026-11-19)**: A1 `Thermal_zone` (PR #45, merged) → A2
  `Load_space` → A3 infiltration check → A4 comparison with the building / defaults → A5
  editor graph, docs, gallery example 08; then the water plant B1 `Boiler` → B2
  `HVAC_water_generator` (compatibility break) → B3 several generators → B4 primary /
  secondary → B5 `HVAC_water_circuit` → B6 variable flow → B7 notebooks, docs, 0.10.0. No
  0.9.1. Test projects in `~/Desktop/opensimula_0.10/` (made by scratchpad scripts).
- **A2 done (branch `feat/load-space`)**: `Load_space` as designed (the A3 infiltration
  correction is in it already). Checks:
  - record of the example 05 box at 24 °C / 50 % with an ideal system, fed back to a
    `Load_space` with the same ideal system: T = 24, RH = 50, system heat = record to 1e-12 W.
  - against ASHRAE 140 (Denver), record at 24 °C, `Load_space` with no system vs 600FF/900FF
    and with the 20/27 °C ideal system vs 600/900 (envelope conductance of the box 1.8
    W/(m²·K) of floor, 6 exposed faces):
    - heavy box 900: ISO `MEDIUM` gives heating 1.44 / cooling 2.24 MWh vs 1.64 / 2.61, free
      floating rms 2.1 K (`CUSTOM` 165 kJ, A_m 1.5: rms 1.8 K).
    - light box 600: every ISO class is too heavy (VERY_LIGHT: 3.25 / 4.71 MWh vs 4.31 /
      5.97, rms 7 K); `CUSTOM` 15-20 kJ/(m²·K), A_m 1.0 gives 4.18 / 5.93 MWh, rms 1.8 K. The
      case 600 box is lighter than any real building (decided 2026-11-19: keep the ISO
      classes and `MEDIUM` as default; the examples' box uses `CUSTOM` 20 / 1.0, U 1.8).
  - examples 05/06 box in Sevilla with `CUSTOM` 20 / 1.0, U 1.8: free-floating rms ~1.1-1.5 K
    while closed, cooling within 2-3 %.
  - ISO 13790 table 12 values confirmed by secondary sources (a thesis transcribing chapter
    12.2, the Modelica Buildings ISO13790 docs).
- **Fixed (own commit, branch `feat/load-space-docs`)**: `File_data` with `file_step`
  "SIMULATION" did not reset the row index between columns: when n_time_steps was not a
  multiple of the rows, the second and later columns were shifted. Regression test in
  `test/test_File_data.py` (50 steps, 24 rows).
- **A5 done (branch `feat/load-space-docs`)**: `Load_space` in the "Building" family of the
  editor graph; page in `component_list_building.md` (model, defaults, table against
  ASHRAE 600/900); air systems docs say Space or Load_space (and `spaces` for the perfect
  and DX systems, documented as `space` before); gallery example **08 Load records** (the
  DX of 06 with the box replaced by `office_loads.csv`, shipped, `*.csv` in package-data and
  copied by `opensimula examples`): cooling 5722 vs 5612 kWh, DX 2631 vs 2569 kWh, 20 vs 18
  hours above 25.5 °C, heating 300 vs 188 kWh; simulates in half the time (3.4 vs 7.3 s).
  Figure `mkdocs/img/examples/08_load_records.png` (scratchpad `ex/figure08.py`).
- **Follow-up**: the results viewer exports CSV columns as `office.system_sensible_heat
  [W]`; `File_data` reads them, but a name with a dot cannot be used in
  `input_variables`. The docs say to rename the columns; better: `File_data` could replace
  the dots, or the viewer export short names.

## Planned: `Energy_indicators`, and `CTE_compliance` on top of it (design closed 2026-11-23)

Goal: from a simulation, the energy use of a project as final energy per carrier and
service, primary energy (non-renewable and total) and CO₂, per m², with a report. Two
components, kept apart (decided):

- **`Energy_indicators`** (0.11): neutral, not tied to a country or a regulation. Counts
  the energy each consumer uses, converts it with configurable factors and reports it.
- **`CTE_compliance`** (later): uses an `Energy_indicators` and adds the Spanish CTE DB-HE
  rules: which services count (lighting only in tertiary buildings), reference systems for
  the heat without equipment, regional factors, limits per climate zone (C_ep,nren,
  C_ep,tot, hours outside setpoint), and maybe HE1 envelope indicators (K global,
  q_sol,jul: the geometry is there). Not a certification tool (HULC stays the official
  one). Fully backwards compatible: new components, nothing existing changes.

What consumes energy today (checked 2026-11-23):

- `HVAC_DX_system`: `power` (electric, compressor + indoor fan; fan alone when venting) and
  `indoor_fan_power` (already inside `power`); `state` gives heating/cooling.
- `HVAC_SZW_system`, `HVAC_MZW_system`: `supply_fan_power`, `return_fan_power` (electric).
  The heat of their coils (and MZW reheat) is consumption only through a plant
  (`water_source = WATER_SYSTEM`); with `UNKNOWN` it has no generator.
- `HVAC_water_generator`: `power` (electric, equipment), `fuel_power` (LHV, boilers, carrier
  = `Boiler.fuel`, `FUELS` includes ELECTRICITY), `pump_power`; `state` heating/cooling.
- `HVAC_water_system`: `secondary_pumps_power`; `pumps_power`, `generators_power`,
  `generators_fuel_power`, `electric_power` are sums of its generators (**double counting
  risk** if both plant and generators are added up).
- `HVAC_water_circuit`: `pumps_power`.
- `HVAC_perfect_system`: only heat (`Q_sensible`, `Q_latent`), no equipment.
- `Space`: `light_convective + light_radiant` = lighting; `other_gains_*` = equipment.
  `Load_space`: nothing.
- Not modelled: DHW, on-site PV / renewables, humidifiers.

Decisions (2026-11-23):

1. **Consumers report themselves**: each consumer implements a common method, e.g.
   `get_energy_use(time_index)` → list of `(carrier, service, W)`. `Energy_indicators`
   needs no table of variable names per type, and each power is counted once (the plant
   reports only its own secondary pumps, each generator its equipment and its pump).
2. **Services**: HEATING, COOLING (energy of the equipment: compressors, boilers),
   **WATER_TRANSPORT** (all pumps), **AIR_TRANSPORT** (all fans, the DX indoor fan taken
   out of `power`), LIGHTING, EQUIPMENT, plus the user's own (e.g. DHW). Transport is
   **not** assigned to heating/cooling/DHW in the simulation: that is done afterwards, in
   `report()`, with a hypothesis given as an argument (e.g. by the mode of the system at
   each hour, or kept apart).
3. **Heat without equipment** (perfect system, coils with `UNKNOWN` source): its own
   services (e.g. HEATING_WITHOUT_EQUIPMENT, COOLING_WITHOUT_EQUIPMENT), thermal energy
   with no carrier. Converted to final energy only in `report()`, with reference
   generators given as arguments (carrier + efficiency / EER); `CTE_compliance` will pass
   the CTE ones. Without them, the report shows them as thermal energy, out of the primary
   energy and CO₂ totals.
4. **Equipment** (`other_gains_*` of the spaces, convective + radiant + latent): electric
   by default; a parameter (e.g. `equipment_carrier`) sets another carrier.
5. **Lighting** always counted in `Energy_indicators` (whether it enters the CTE indicator
   is a `CTE_compliance` rule).

Proposed parameters of `Energy_indicators` (to refine when coding):

- `components`: consumers to count; empty = all of the project.
- `zones`: `Space`/`Load_space` giving the reference area (sum of `floor_area`) and their
  lighting and equipment; empty = all.
- `equipment_carrier`: ELECTRICITY by default.
- Conversion factors per carrier (fp,nren, fp,tot, kg CO₂/kWh): a preset name or a custom
  table; the Spanish presets (PENINSULA, BALEARES, CANARIAS, CEUTA_MELILLA) in a data
  module that `CTE_compliance` reuses.
- `extra_uses`: `input_variables` + expressions per carrier and service (DHW from a
  record or a `Calculator`...), as `Space_type` / `Calculator`.
- Hourly variables: final energy per carrier and per service, primary nren and total,
  CO₂ (heat without equipment kept apart, decision 3). Last in the order (before or after
  `Calculator`, to decide).
- `report(frequency="yearly", per_area=True, transport=..., reference_heating=...,
  reference_cooling=...)` → table (DataFrame) by service and carrier, also for the GUI.

6. **Comfort in its own component** (e.g. `Comfort_indicators`): hours outside setpoint per
   zone while its system is on, `unmet_sensible_heat` of `Load_space`; later operative
   temperature, PMV/PPD. It is not energy; `CTE_compliance` will use both.
7. **Heat without equipment reported by each system**: `HVAC_perfect_system` its
   `Q_sensible` + `Q_latent`; `HVAC_SZW_system` / `HVAC_MZW_system` with `UNKNOWN` source
   the heat of their coils (and reheat), heating and cooling apart.
8. **Ambient energy of heat pumps** (added 2026-11-23): it counts in final and primary
   energy (renewable). Carrier AMBIENT (fp,ren 1, fp,nren 0, no CO₂). In heating it is the
   heat given minus the electricity of the compressor (`HVAC_DX_system`,
   `HVAC_water_generator` with a `Chiller_heat_pump`). Whether a heat pump counts as
   renewable (seasonal performance threshold) is a `CTE_compliance` rule. **Cooling: no
   ambient energy** (as the CTE does), decided 2026-11-23.
9. **`report()`** (decided 2026-11-23):
   - Transport arguments, one for water and one for air (e.g. `water_transport`,
     `air_transport`): "SEPARATE" (**default**, kept as their own services) or "BY_MODE"
     (assigned to heating/cooling by the mode of the system at each hour; what runs with
     no load stays in the transport service). `CTE_compliance` sets them as it needs.
   - Tables: annual final energy by service and carrier, **monthly final energy** (months ×
     carrier and service), primary energy (nren, total) and CO₂ by service, per m² and
     total. THERMAL (heat without equipment) shown apart, converted only with reference
     generators given as arguments.
   - **HTML**: the result is an object holding the DataFrames with `to_html()` and
     `_repr_html_()`, so it shows as formatted tables in Jupyter/marimo and in the GUI.
   - A preview script with `get_energy_use()` (example 09: 101 kWh/m² C_ep,nren, 127
     C_ep,tot, 17.2 kg CO₂/m², renewable share 20.6 %) checked the shape of the tables.

Conversion factors, **checked 2026-11-23** against the documento reconocido del RITE
"Factores de emisión de CO₂ y coeficientes de paso a energía primaria de diferentes fuentes
de energía final consumidas en el sector de edificios en España" (version 20/07/2014, in
force since 14/01/2016; tables of section 8, pp. 16-17). Per kWh of final energy:

| Carrier | fp,ren | fp,nren | fp,tot | kg CO₂/kWh |
|---|---|---|---|---|
| Electricity, peninsular | 0.414 | 1.954 | 2.368 | 0.331 |
| Electricity, Baleares | 0.082 | 2.968 | 3.049 | 0.932 |
| Electricity, Canarias | 0.070 | 2.924 | 2.994 | 0.776 |
| Electricity, Ceuta y Melilla | 0.072 | 2.718 | 2.790 | 0.721 |
| Electricity, national (statistics only) | 0.396 | 2.007 | 2.403 | 0.357 |
| Electricity, extrapeninsular (statistics only) | 0.075 | 2.937 | 3.011 | 0.833 |
| Diesel (gasóleo calefacción) | 0.003 | 1.179 | 1.182 | 0.311 |
| LPG | 0.003 | 1.201 | 1.204 | 0.254 |
| Natural gas | 0.005 | 1.190 | 1.195 | 0.252 |
| Coal | 0.002 | 1.082 | 1.084 | 0.472 |
| Biomass, not densified | 1.003 | 0.034 | 1.037 | 0.018 |
| Biomass, densified (pellets) | 1.028 | 0.085 | 1.113 | 0.018 |

The document does not say HHV or LHV for the fuels; the boilers here work on the LHV
(as the CTE tools). `Boiler.fuel` has one BIOMASS: map it to pellets or add both (and
COAL) when coding the factors.

Design closed (2026-11-23). Order of work: (1) `get_energy_use()` in the consumers, with
tests; (2) `Energy_indicators` and `report()`; (3) `Comfort_indicators`; (4) docs and a
gallery example; later `CTE_compliance`.

- **Step 1 done (branch `feat/energy-use`)**: `opensimula/energy.py` (`CARRIERS`,
  `SERVICES`, `Energy_use(carrier, service, values)`), `Component.get_energy_use()`
  (returns the arrays of the whole simulation, not one time step: it reads the stored
  variables, so it works after `simulate()`) implemented in `Space`, `HVAC_DX_system`,
  `HVAC_SZW_system`, `HVAC_MZW_system`, `HVAC_perfect_system`, `HVAC_water_generator`,
  `HVAC_water_system` (secondary pumps only), `HVAC_water_circuit`. Tests in
  `test/test_energy_use.py` (each power counted once against the plant totals).
  **Core fix found here (own commit):** cooling coils of SZW/MZW gave the plant only their
  sensible heat, not the latent (condensation); also T_ow in cooling and the SZW water
  temperature with a plant. Fan coil test: cooling generation +11.8 %; examples 07/09:
  chiller electricity +3.6/+3.8 %. ASHRAE 140: 0 changed.
- **Step 2 done (branch `feat/energy-indicators`)**: component `Energy_indicators` (last in
  `DEFAULT_COMPONENTS_ORDER`, after `Calculator`, so a calculator can feed its extra uses).
  Parameters: `components` / `zones` (empty = all), `reference_area` (0 = floor area of the
  zones), `equipment_carrier`, `conversion_factors` (PENINSULA, BALEARES, CANARIAS,
  CEUTA_MELILLA, NATIONAL, EXTRAPENINSULAR) + `custom_carriers` / `custom_fp_ren` /
  `custom_fp_nren` / `custom_CO2` (override), `input_variables` + `extra_services` /
  `extra_carriers` / `extra_expressions` (W, evaluated in `post_iteration`). Hourly
  variables filled in `post_simulation` from `get_energy_use()`: one per carrier
  (`electricity`, `natural_gas`, `ambient`, `thermal`...), one per service (final energy,
  without AMBIENT), `primary_ren`, `primary_nren`, `primary_total` (W), `CO2` (kg/h).
  `report(water_transport, air_transport, reference_heating, reference_cooling)` →
  `Energy_report` (`annual`, `monthly_carriers`, `monthly_services`, `indicators`,
  `indicators_per_area`, `summary`, `notes`; `to_html()`, `_repr_html_()`). `Energy_use`
  got a `mode` (1/-1/0) for the transport, the plant tells its generators who it is
  (`g.plant`). The GUI shows the report of each `Energy_indicators` after Simulate (an
  accordion, default hypotheses), checked in Chrome. Notebook
  `jupyter_test/ENERGY_INDICATORS.ipynb`. Example 09 (year): 101.1 kWh/m² C_ep,nren,
  127.3 C_ep,tot, 17.2 kg CO₂/m², renewable share 20.6 %.
- **Step 3 done (branch `feat/comfort-indicators`)**: component `Comfort_indicators` (last
  in the order). `Component.get_zone_setpoints()` → `Zone_control(zone, heating_setpoint,
  cooling_setpoint, on)` (module `opensimula/comfort.py`) in DX, SZW, perfect system and
  MZW (each zone its `spaces_setpoint`, the same for heating and cooling). Parameters:
  `zones` (empty = all), `tolerance` (0.5 K; must be above the zone convergence, 0.01 K:
  with 0 the hours held at the setpoint count, 43 % in example 06), `only_system_on`,
  `input_variables` + `period` (e.g. occupied hours). Variables `outside_<zone>` (1/-1/0)
  and `zones_outside`. `report()` → `Comfort_report` (`zones`: hours counted / above /
  below / outside, %, degree-hours, T max/min; `monthly`; `summary`; HTML). Shown in the
  GUI after Simulate with the energy report. Example 06: 18 h of 2380 (0.8 %), as the
  gallery says; 09: 3 h. **Left out**: the unmet load of `Load_space`
  (`unmet_sensible_heat` is the record at T_ref minus the system, it counts the load not
  needed when the zone floats between setpoints: 930 kWh "unmet" in 09 with 3 h outside).
  Notebook `jupyter_test/COMFORT_INDICATORS.ipynb`. Later: operative temperature, PMV/PPD.
- **Step 4 done (branch `docs/indicators`)**: docs of both components in
  `component_list_utils.md` (what each component reports, factors, report()), user guide
  section "Energy and comfort indicators", developer guide note on `get_energy_use()` /
  `get_zone_setpoints()`, gallery example `10_energy_and_comfort` (09 + the two
  components; year: 5010 kWh final, 52 kWh/m², 101.1 / 127.3 kWh/m² primary nren / total,
  17.2 kg CO₂/m², 20.6 % renewable, 3 h outside of 4760) with its figure (monthly final
  energy by service; heating red, cooling blue, as the user wants in every figure).
  **Next**: `CTE_compliance` (rules of DB-HE on top of both: services counted, reference
  systems, limits per climate zone, tolerance of the hours outside setpoint).
- **Follow-up**: sign conventions of the system outputs differ (in cooling, SZW/MZW
  `Q_sensible` negative and `Q_latent` positive, DX both positive, perfect system both
  signed): worth unifying before 1.0 (breaks outputs).

## Planned: domestic hot water (DHW) and solar thermal (design closed 2026-11-24)

Step 2 of the plan of 2026-11-24. DHW counts in HE0, HE4 asks for a renewable share
(60-70 % of the demand), and nearly every HULC building has it (the TFG test building:
gas boiler, 120 l/day at 60 °C).

**Approach (decided): DHW on the water plants we have**, no separate DHW system. A DHW
demand is one more "coil" of a plant or circuit: it takes the flow m at the supply
temperature and gives it back at the mains temperature (the water drawn is replaced by
mains water), so the plant's own balance gives the generators an inlet at the mains
temperature (a condensing boiler in instantaneous DHW works as it should). Generators,
sequencing, pumps, circuits and energy accounting are reused.

Components and changes:

1. **`DHW_demand`** (new): `water_system` (a plant or a circuit, like the coils); daily
   volume at the reference temperature (expression, l/day; 60 °C by default; allows
   schedules); hourly profile (24 fractions, default the Anejo D table c of the DB-HE);
   mains water temperature (12 monthly values or an expression; a helper with the Anejo G
   table by province capital and the altitude correction); `distribution_losses` (fraction
   of the demand, default 0) for networks without recirculation. Load
   m·cp·(T_ref − T_mains)·(1 + losses) added to the plant each iteration; demand not met
   when the water is colder than the use temperature (reported).
2. **`Water_tank`** (new, equipment / data like `Boiler`): volume, loss coefficient UA,
   temperature of the room it is in (expression), number of nodes (1 = fully mixed, the
   default; stratified later). Referenced by a plant or a circuit with a new `tank`
   parameter: then its water is the tank (replaces `total_water_volume` / `water_volume`)
   and its losses are UA·(T − T_room) (on top of `Q_loss`). Also the buffer tanks of
   heating plants.
3. **Where the tank goes**:
   - DHW only with storage (boiler + tank, electric water heater, DHW heat pump): `tank` in
     the plant; the generators heat it to the setpoint, the demand draws from it.
   - Heating + DHW with storage (boiler or heat pump with a DHW tank, central DHW): `tank`
     in a DHW charging circuit hanging from the plant (its pump = charging pump, its
     setpoint = the tank setpoint); heating on other circuits. To check / adapt: the
     circuit must charge its tank to the setpoint (today it mixes to a supply setpoint).
   - Instantaneous (boiler without tank): plant with a small water volume and setpoint
     60 °C.
   - Electric water heater: a `Boiler` with fuel ELECTRICITY and efficiency 1.
4. **Recirculation**: the DHW circuit's `Q_loss` (loop losses) and its pump (recirculation
   pump); nothing new.
5. **Plant changes**: energy of the generators split by service, HEATING and DHW, by the
   heat delivered to each kind of load each hour (also needed for combined plants);
   optional DHW priority (when the generators fall short, DHW loads first).
6. **Solar thermal**: `Solar_collector` (equipment: area, tilt, azimuth, EN ISO 9806
   quasi-steady efficiency η0, a1, a2 and incidence angle modifier b0; radiation from
   `File_met`) used by an `HVAC_water_generator` as a **non-controllable generator**: it
   gives what the sun allows when the collector is hotter than the tank (on/off by
   temperature difference, its loop pump), the plant always takes it (up to a maximum
   temperature) and the other generators make up the rest (first in the sequencing). New
   carrier **SOLAR_THERMAL** (renewable: fp,ren 1, fp,nren 0, no CO2), service DHW.
   Stratified tank with this step (demand draws at the top and mains water enters at the
   bottom; solar heats the bottom; the backup the top); examples with 4-6 nodes.
7. **Ambient energy** of heat pumps counts in DHW (DB-HE).
8. Limits: one mode per plant (heat or cold): DHW in summer needs its own plant if the
   climate plant cools ("3 in 1" heat pumps alternating, later). Potable water and closed
   loop are not told apart (energy is what matters here); a heat exchanger later, if
   needed, through a circuit.

Order: (1) `DHW_demand` and the split of energy by service, with an example of a combined
boiler (**done 2026-11-24**, branch `feat/dhw-demand`: `DHW_demand` (volume flow
and use temperature as expressions, the Anejo D profile as schedules from
`cte.dhw_profile_schedules()`, Anejo G monthly mains of Sevilla by default, distribution
losses; water hotter than the use temperature mixed with mains water, colder used as it
comes with the rest `Q_unmet` and the `low_temperature` flag; nothing while the plant
cannot heat); `add_coil_load(Q, flow,
dhw)` in plants and circuits, variable `Q_dhw`, `HVAC_water_system.dhw_share()`;
generators and pumps split their energy HEATING/DHW (`energy.split_dhw`), transport mode
2 = DHW for `BY_MODE`; service DHW in `SERVICES`. Test cases in `pruebas/2026-11-24_acs`:
instantaneous boiler 2226 kWh/year of demand, 2023 kWh of gas; DHW on the two-pipe plant
of example 10: 521 kWh unmet in summer. Found: the plants work with constant flow, so a
boiler's inlet is a mixture, not mains water (efficiency of condensing boilers): variable
flow (B6) fixes it); (2) `Water_tank`, DHW charging circuit, DHW priority (**done 2026-11-24**,
branch `feat/water-tank`: `Water_tank` (volume, UA with the conversion from the ErP / EN 12897
standing losses in its docs, `ambient_temperature` expression, thermostat `dead_band`);
`tank` in the plant (its water; the plant works as with a header, the loads moving the water
without secondary pumps) and in the circuit (charging circuit, `tank_setpoint`: charges the
fraction of the step needed, the tank gives water while the plant is off); plants and
circuits with only DHW loads count all their energy as DHW (`is_dhw_only()`, also tank
losses); **DHW priority left out (option A, 2026-11-24)**: the loads share a shortfall.
Found: without dead band a tank recharges every hour and the plant pump runs all year
(ON_LOAD is per time step): use a dead band of 5-7 K); (3) solar thermal, with
the stratified tank, split on 2026-11-24 into **3a done** (branch `feat/solar-thermal`:
`Solar_collector` (EN ISO 9806 η0, a1, a2, IAM b0 and K_d, tilt, azimuth from the south,
heat exchanger effectiveness, `max_temperature`; T_m from the inlet, flow and
effectiveness, quadratic solved in closed form), the generator with a collector is not
controllable (the plant with a tank always takes its heat, the others give the rest),
carrier SOLAR_THERMAL (1/0/0 as AMBIENT; not in the RITE document), `DHW_demand.
preheat_system` (series backup: the backup heats from the preheat temperature). Fixed on
the way: a plant with a tank gave its setpoint, not the tank temperature, in the first
iteration. Sevilla, 2 m², 150 l, 120 l/day: 1938 kWh/m² on the plane, collector 0.47,
solar fraction 0.72 (0.54 December, 0.95 August)) and **3b done** (branch
`feat/stratified-tank`: `Water_tank.number_of_nodes`, `backup_position`; in a plant only
(circuits: error); per time step from the nodes at its start: draw advected (sub-steps
of at most a node, two passes so that the return temperature gives the load exactly),
losses per node, solar on the bottom node (capped by bisection at max_temperature),
backup on its node up to the setpoint by bisection, inversions mixed (pool adjacent
violators); variables T_node_i. Single 200 l tank, 2 m², electric heater in the middle,
Sevilla: solar fraction 0.56 with 1 node, 0.72 / 0.74 / 0.75 / 0.76 with 2 / 4 / 6 /
10; balance exact. Later: stratified charging circuits, solar return to the node of its
temperature, pump heat in stratified tanks); (4) HE4 in `CTE_compliance` (renewable share of the DHW demand,
on-site and nearby perimeter, SCOP_dhw ≥ 2.5 for heat pumps) and the Anejo F reference
demand helper (28 l/day·person, occupancy by bedrooms, centralisation factor) (**done 2026-11-24**, branch `feat/cte-he4`: demand = heat of the
generators to DHW + unmet; renewable: solar, heat pumps Q − E if seasonal SCOP_dhw of the
simulation ≥ 2.5, biomass Q·fp,ren/fp,tot; 70 % / 60 % below 5000 l/day, applies above
100 l/day (`dhw_daily_demand` or from the DHW_demand components at 60 °C); helpers
`dhw_reference_demand`, `mains_temperatures` (Anejo G, 52 capitals, altitude correction),
`he4_minimum_share`; report title HE0 and HE4 and table per generator). Later:
legionella cycles, "3 in 1" heat pumps.

## Planned: `CTE_compliance`, verification of DB-HE (design closed 2026-11-23)

Goal: check a project against the Spanish DB-HE 2019 (articulado 14/06/2022), on top of
`Energy_indicators` and `Comfort_indicators`. Verification only; the energy rating
(RD 390/2021, letters A-G) would be another component (`Energy_rating`) on the same base.
Not a recognised procedure: HULC / CE3X stay the official tools (the DB-HE says the
verification "no es necesario que se trate de procedimientos oficialmente reconocidos",
the rating does need them). Sources given by the user: DB-HE con comentarios (22/12/2023)
and Guía de aplicación DB-HE 2019 (junio 2022). Values below copied from them.

**Phase 1: HE0** (`report()` → table: requirement, value, limit, complies).

- Indicators per m² of reference area: sum of the useful floor area of the habitable
  spaces inside the thermal envelope (HE0 4.6); spaces with process conditions may be
  excluded. Uses with different limits are checked apart (no compensation): one
  `CTE_compliance` per use part, each with its own `Energy_indicators` (`zones` subset).
- EPB services counted (HE0 4.1.3, Guía 4.3): heating, cooling, DHW, ventilation,
  humidity control; lighting only in uses other than residencial privado. Equipment
  (appliances), lifts... not counted. Ambient energy of heat pumps only in heating and
  DHW (already so in `get_energy_use()`). Monthly balance and kexp = 0 (matter only with
  on-site production: no PV model yet).
- Reference systems, residencial privado only, when a service has no system (HE0 4.5,
  table 4.5): heat and DHW natural gas, efficiency 0.92 **on the HHV (PCS)**; cold
  electricity, 2.60 (nominal values).
- C_ep,nren,lim [kWh/m²·year] (tables 3.1.a/b-HE0), winter zone α / A / B / C / D / E:
  - residencial privado, new and extensions: 20 / 25 / 28 / 32 / 38 / 43;
    changes of use to residential and reforms: 40 / 50 / 55 / 65 / 70 / 80;
    extrapeninsular (Baleares, Canarias, Ceuta, Melilla) × 1.25.
  - other uses: 70 / 55 / 50 / 35 / 20 / 10 + 8·C_FI; extrapeninsular × 1.40.
- C_ep,tot,lim (tables 3.2.a/b-HE0):
  - residencial privado, new and extensions: 40 / 50 / 56 / 64 / 76 / 86;
    changes of use and reforms: 55 / 75 / 80 / 90 / 105 / 115; extrapeninsular × 1.15.
  - other uses: 165 / 155 / 150 / 140 / 130 / 120 + 9·C_FI; extrapeninsular × 1.40.
- C_FI, carga interna media [W/m²] (Anejo A): mean hourly load over a typical week of
  occupancy (sensible only), lighting and equipment, weighted by useful area. Levels: low
  < 6, medium 6-9, high 9-12, very high ≥ 12. Residential ≈ 4 W/m².
- Hours outside setpoint (HE0 4.1.6, Anejo A): ≤ 4 % of the occupation time (residential
  24 h: 350 h/year). An hour counts when **any** conditioned habitable space is more than
  **1 °C** outside its setpoint range during occupation: it measures time, not area
  (several spaces at once count once). `Comfort_indicators` today adds zone-hours: it
  needs the building count (hours with `zones_outside` > 0).
- Residential operational conditions and profiles (Anejo D): setpoints low 17 °C (0-7 h,
  23-24 h) / 20 °C (7-23 h) Oct-May; high 27 °C (0-7 h, 23-24 h) / 25 °C (15-23 h)
  Jun-Sep, free 7-15 h; loads by hour (occupancy sensible/latent, lighting, equipment)
  and DHW profile by hour. Tertiary: the project's, or the normalised profiles of the
  documento reconocido "Condiciones técnicas..." (8/12/16/24 h, low/medium/high load).
- DHW reference demand (Anejo F): residential 28 l/day·person at 60 °C, occupancy by
  bedrooms (1: 1.5, 2: 3, 3: 4, 4: 5, 5: 6, 6: 6, >6: 7), centralisation factor by number
  of dwellings; other uses table c (offices 2 l/day·person...); mains water temperature
  by month and province capital (Anejo G).
- Climate zone (Anejo B) by province and altitude: winter letter α / A-E + summer 1-4.

**Phase 2: HE1** (geometry and constructions are in the model):

- K = Σ b_tr·(A·U + l·ψ + χ) / Σ b_tr·A (b_tr 0 for elements next to other buildings or
  adjacent spaces outside the envelope); K_lim tables 3.1.1.b (residential: new
  V/A ≤ 1: 0.67 / 0.60 / 0.58 / 0.53 / 0.48 / 0.43, V/A ≥ 4: 0.86 / 0.80 / 0.77 / 0.72 /
  0.67 / 0.62; changes of use and reforms > 25 %: 1.00 / 0.87 / 0.83 / 0.73 / 0.63 / 0.54
  and 1.07 / 0.94 / 0.90 / 0.81 / 0.70 / 0.62) and 3.1.1.c (other uses: 0.96 / 0.81 /
  0.76 / 0.65 / 0.54 / 0.43 and 1.12 / 0.98 / 0.92 / 0.82 / 0.70 / 0.59), linear in V/A
  between 1 and 4. Alternative: heating and cooling demand both < 15 kWh/m².
  Thermal bridges ψ are not modelled: to decide (lengths × ψ given by the user, or none).
- U_lim per element (table 3.1.1.a): walls/floors to outdoor air 0.80 / 0.70 / 0.56 /
  0.49 / 0.41 / 0.37; roofs 0.55 / 0.50 / 0.44 / 0.40 / 0.35 / 0.33; to ground or
  non-habitable 0.90 / 0.80 / 0.75 / 0.70 / 0.65 / 0.59; openings 3.2 / 2.7 / 2.3 / 2.1 /
  1.8 / 1.80; doors ≤ 50 % glazed 5.7.
- q_sol;jul ≤ 2.00 (residential) / 4.00 (other) kWh/m²·month: July solar gains through
  openings with movable shading active / reference area (could come from a July
  simulation with shading on, or the simplified formula).
- n50 (new residential > 120 m²): ≤ 6 (V/A ≤ 2) to 3 (V/A ≥ 4) h⁻¹; Anejo H n50 = 0.629
  (C_o·A_o + C_h·A_h)/V_int, C_o 16 (new) / 29 (existing) m³/h·m² at 100 Pa. Q100 of
  openings ≤ 27 (α-B) / 9 (C-E).

Decisions (2026-11-23):

1. **Phase 1 is HE0 only**: `report()` gives three checks, C_ep,nren, C_ep,tot and hours
   outside setpoint (value, limit, complies). HE1 in phase 2.
2. **Hours outside setpoint**: `Comfort_indicators` gets the building count (hours with
   any zone outside, `zones_outside` > 0) besides the zone-hours; `CTE_compliance` uses
   it with tolerance 1 K and the occupation time (period expression of the comfort
   component; residential 24 h).
3. **Transport**: `CTE_compliance` calls `report(water_transport="BY_MODE",
   air_transport="BY_MODE")`: pumps and fans go to heating/cooling by the mode of each
   hour; fans running with no load stay as AIR_TRANSPORT, counted as the ventilation
   service (EPB).
4. **C_FI** (other uses): computed from the `Space` gains (occupancy sensible, lighting,
   equipment, per m² of the zones) as the mean of the simulated period; a parameter can
   give it; required for `Load_space` zones (they have no breakdown).
5. **Parameters**: `energy_indicators`, `comfort_indicators`, `climate_zone` (e.g. "B4",
   given by the user; an Anejo B lookup by province and altitude can come later),
   `building_use` (RESIDENTIAL_PRIVATE / OTHER), `intervention` (NEW_OR_EXTENSION /
   CHANGE_OF_USE_OR_REFORM). Extrapeninsular multipliers from the `conversion_factors`
   region of `Energy_indicators` (BALEARES, CANARIAS, CEUTA_MELILLA, EXTRAPENINSULAR).
6. **DHW**: entered by the user as an extra use of `Energy_indicators` for now; a helper
   for the Anejo F/G reference demand later.
7. Residential without a system for a service: the reference systems of table 4.5 as
   `reference_heating` / `reference_cooling` of the report.

**Fuel basis (confirmed by the user 2026-11-23)**: final energy for primary energy and
CO₂ is on the **LHV (PCI)**, as the boilers here and the RITE factors: nothing to
convert. The HHV (PCS) appears only in the reference boiler of the substitution systems
(0.92 on the PCS): its final energy on the PCI is Q / (0.92 · PCS/PCI); PCS/PCI of
natural gas ≈ 1.11 (to check the exact value the CTE tools use; a parameter of
`CTE_compliance` with that default).

Order of work: (1) building count of hours in `Comfort_indicators` (**done**, branch
`feat/comfort-building-hours`: BUILDING row and column, `building_*` summary, variable
`building_outside`); (2) **done** (branch `feat/cte-compliance`): `CTE_compliance` HE0, module
`opensimula/cte.py` (tables, `he0_limits()`, `CTE_report`); EPB services (equipment out,
lighting only for other uses; `non_epb_services`), transport BY_MODE, residential
reference systems (gas 0.92 HHV × `hhv_lhv_ratio` 1.11, electricity EER 2.60), C_FI
from the Space gains or `internal_load` (required with Load_space), extrapeninsular from
the factors region, hours outside setpoint = building hours of the comfort component vs
4 % of its period hours (`period_hours`; set its `period` to the occupation of tertiary
buildings), warning if its tolerance is not 1 K; GUI shows the report. Example 06 as
an office in B4: C_ep,nren 151 vs 104 kWh/m² (fails, cooling 94), C_ep,tot 186 vs 211,
10 h outside; (2) `CTE_compliance`
HE0 with tests (cases with known limits: residential new B4, other uses with C_FI);
(3) docs and a gallery example (residential, Anejo D profiles?); (4) phase 2, HE1.

## B6: variable water flow (agreed 2026-11-24)

Moved ahead of DHW steps 2-3: an instantaneous boiler (no tank, no pump, mains pressure)
must see only the water drawn, at the mains temperature (condensing boilers).

- **`flow_control`** in `HVAC_water_system` and `HVAC_water_circuit`: `CONSTANT`
  (default, the current behaviour, bit-identical) or `VARIABLE` (two-way valves).
- **`minimum_flow`** (fraction of the design flow, default 0): the flow never goes below
  it while the plant (circuit) is on; a `Q_process` without flow needs it > 0 (warning).
- **Plant without header, VARIABLE**: loop flow = flow asked by the coils, circuits and
  DHW demands (`coils_flow`), limited to [minimum, design]; 0 → the water stands (only
  losses). Generators share it in proportion to their nominal flow; their pumps at that
  flow (`F_water` in the pump `power_expression`). `pump_operation` does not apply.
- **Plant with header, VARIABLE**: secondary flow = `coils_flow` limited to [minimum,
  secondary design]; secondary pumps staged: in the order of the list, as many as needed
  (cumulative nominal flow ≥ flow), sharing the flow in proportion to their nominal flow.
  Primary unchanged (each generator at its nominal flow while it runs, bypass).
- **Circuit, VARIABLE**: its flow = that of its coils limited the same way, its pumps
  staged as the secondary ones.
- Checks: CONSTANT bit-identical (tests, ASHRAE 140 quick check 0 changes); instantaneous
  boiler VARIABLE: T_generators_in = T_mains while drawing, energy balance; header and
  circuit: less pump power than at constant flow; test case in `pruebas/` (condensing
  instantaneous boiler, constant vs variable).

## Future: help links in the GUI (added 2026-11-24)

Idea of the user: in the editor, each parameter field with a help link to the description
of that parameter in the documentation; the same for the variables of the results viewer,
which are only seen in its tree.

- **Targets**: today the component pages (`component_list_*.md`) have an anchor per
  component (`### DHW_demand` → `#dhw_demand`) but the parameters and variables are list
  items without anchors. Options: (a) add anchors by hand (`attr_list`:
  `- **daily_volume** {#dhw_demand-daily_volume}`); (b) better: one source, a short
  description for each parameter and variable in the code (`add_parameter(...,
  description=...)`, `Variable(..., description)` already has one) and the component
  pages generated from it (a mkdocs hook or a script), with anchors
  `<type>-<parameter>`; the editor and the viewer then show the description as a tooltip
  and link to the anchor.
- **Map type → page**: each component type belongs to one page (building, HVAC air, HVAC
  water, utils...): a table in the code (or the generator writes it).
- **Editor**: a small "?" next to each field (tooltip with description and unit, click
  opens the docs at the anchor; the docs URL of the installed version).
- **Results viewer**: the variables are rows of the tree: tooltip on hover (description,
  unit) and a "?" on the row or in the legend of a plotted series; or an info line under
  the tree for the selected variable.
- Docs per version (the published site is the last one): link to the version installed,
  or accept the latest.

## Future: importer of HULC projects (added 2026-11-19)

Code by a student's TFG (final degree project) to import buildings made with HULC (the
Spanish CTE tool, `.ctehexml` files) into OpenSimula, in `future/hulc_to_opensimula/` (not
part of the package yet):

- `hulc_to_opensimula.py`: reads the `.ctehexml` (XML header with the general and climate
  data + a CDATA block in BDL, the LIDER / DOE-2 language) and converts materials, glazings,
  constructions... to the dict of `Project.read_dict()` (phases 1-2).
- `hulc_geometria.py`: geometry (phase 3): floors, spaces, walls, roofs and windows from the
  BDL tree, local HULC coordinates to world and to OpenSimula, CTE schedules, space
  conditions and space types.
- `ajustes_hulc.py`: adjustments of the dict to follow HULC more closely (window U with the
  equivalent frame conductance of each WINDOW, crack infiltration).
- `parche_opensimula_ff.py`: a patch of `Space._create_ff_matrix` for spaces whose floor or
  ceiling is split into several surfaces (rows of the form factor matrix not summing 1,
  long-wave radiation lost). Written against an older version (it mentions 500 iterations
  and no final normalisation; the current code has `_normalize_ff_rows`): **check with the
  TFG building whether the current code still has the problem** before using the patch.
- `Demostracion_HULC_OpenSimula_edificio_v2 .ipynb` (demo), `edificio_pmt_atecyr_sis3.ctehexml`
  (test building), `BDCatalogo.bdc` (HULC catalogue, 630 kB: check whether it can be
  redistributed before committing it). Related: `jupyter_test/EDIFICIO_*_HULC.ipynb` and
  their JSON.

To do when we take it up: review and translate to English (code is in Spanish), tests with
the test building, decide its place (`opensimula.importers.hulc`? a command `opensimula
import-hulc file.ctehexml`), credit the student, and compare the demand with HULC's.

## Growth plan (agreed 2026-10-07)

Strategy: grow first in the **academic** world (research and teaching), then move to
**professional** users (engineering firms, CTE/HULC). There are colleagues at other
universities willing to collaborate, so the project has to be ready to take contributions
from several groups. Work is done step by step; tick items off as they ship.

### 1. Project infrastructure (in progress)

- [x] CI: GitHub Actions runs the tests on Python 3.12 and 3.13 and builds the docs
  (`.github/workflows/tests.yml`), tests badge in the README.
- [x] `CITATION.cff`, `CONTRIBUTING.md` (includes the release steps that were in
  `build_information.txt`), issue and pull request templates.
- [x] Release notes in `mkdocs/index.md` brought up to 0.8.7.
- [x] Removed stray files: `debug.py`, empty root `package-lock.json`.
- [x] Docs published by GitHub Actions (`.github/workflows/docs.yml`) on every change to
  `mkdocs/` on `main`; Pages source is "GitHub Actions", custom domain
  opensimula.jfcoronel.org kept. The generated `docs/` folder is no longer committed.
- [x] Zenodo integration: every GitHub release gets a DOI. Concept DOI
  10.5281/zenodo.23210985 (README badge, `CITATION.cff`); first release v0.8.7.
- [ ] Protect `main` (pull requests + green CI required) once collaborators join.

### 2. Multi-institution collaboration

- [ ] GitHub organization (`opensimula/`) and transfer of the repository (GitHub redirects
  the old URL).
- [ ] Light `GOVERNANCE.md`: lead maintainer, maintainers per area (building envelope, HVAC,
  validation, teaching), decision rule, authorship criteria for joint papers.
- [ ] Plugin registry for components (Python entry points) so other groups can publish
  `opensimula-<something>` packages without touching the core; today a new component must be
  imported in `components/__init__.py`. Template component + template test.
- [ ] `future/` → `contrib/` area for experimental modules (DXF import, etc.).
- [ ] Kick-off meeting with collaborators to split research lines.

### 3. Scientific credibility and publications

- [x] Automated ASHRAE 140 validation: a script that runs every case and generates a
  "Validation" docs page comparing OpenSimula with the reference programs' range
  (all six folders, CI check, v0.8.8; see the section above).
- [x] API reference generated from docstrings (mkdocstrings), 2026-10-28: "API reference"
  section of the docs (`mkdocs/api/`) for Simulation, Project, Component, Parameter_container
  and the parameter types, Variable, Message and Iterative_process; docstrings of their
  public methods completed in Google style. The components' own parameters and variables
  stay in the hand-written Component list. Possible later step: docstrings of the
  component classes themselves, if the Component list is ever generated from code.
- [ ] JOSS paper (multi-author), after items above. **Draft complete (2026-10-28)** in
  `paper/` (PR #20), PDF built by `.github/workflows/draft-pdf.yml`. Authors: J. F. Coronel
  (lead developer, maintainer), L. Pérez-Lombard (HVAC models), I. R. Maestre (envelope
  models). Next: co-authors' review, then submit at joss.theoj.org with the repository URL,
  the version and its Zenodo DOI (a release including `paper/` and the new authors).
- [ ] Full validation paper (JBPS / Energy and Buildings) and conference talks (IBPSA BS,
  BSO, CYTEF).

### 4. Teaching

- [ ] Open course in marimo notebooks exported to WASM (runs in the browser, no install),
  reusing the CYTEF and HULC course material.
- [x] Progressive examples gallery: schedules → weather → walls → windows and gains → ideal
  system → DX → fan coil (2026-11-18, `opensimula examples`, docs page Examples).
- [ ] Spanish and English documentation.

### 5. Research-oriented features

- [ ] Parametric / sensitivity / uncertainty API (project copies, parallel runs, SALib).
- [ ] Calibration against measured data.
- [ ] Step-by-step API and Gymnasium environment for MPC / reinforcement learning.
- [ ] Control components (PID, setpoints, sequences); `Air_distribution`, `Energy_load`.

### 6. Later: professional users

- [ ] HULC import as an official module (now in `jupyter_test/`).
- [ ] gbXML / IFC import.
- [ ] CTE indicators (primary energy, CO₂), comfort indicators, reports.
- [ ] Stable API and versioned project JSON schema from 1.0 on.

## How to resume work here

- `uv sync` to install/refresh the environment, `uv run pytest test` to check everything
  still passes (should be green — see `CLAUDE.md` for the full command list).
- `CLAUDE.md` has the architecture overview (component/parameter/variable model, simulation
  loop, component categories) — read it first if returning after a long break.
- `git log --oneline -20` and open PRs/issues at
  https://github.com/jfCoronel/OpenSimula are the source of truth for what actually shipped;
  this file only tracks what has *not* shipped yet.
