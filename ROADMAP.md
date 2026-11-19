# Development Roadmap

Working notes for resuming development on OpenSimula from any machine. This file is for
the maintainer, not end users — it is not part of the published docs (`mkdocs/`).

## Where things stand (2026-11-13)

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
- **Follow-ups found in B2**:
  - The generator capacity is evaluated at the setpoint, not at the actual supply
    temperature when the water does not reach it (the power is computed at the actual one).
  - A coil only checks the plant's water temperature, not its mode: with SCHEDULE_CONTROL in
    heating, a cooling coil can cool with water that stayed cold (e.g. a hot plant at its
    initial 20 °C in summer) and the plant discards its load: energy from nowhere. Coils
    should ask the plant whether it can heat / cool in its mode.
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
