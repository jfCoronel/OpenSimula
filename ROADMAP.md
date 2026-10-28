# Development Roadmap

Working notes for resuming development on OpenSimula from any machine. This file is for
the maintainer, not end users — it is not part of the published docs (`mkdocs/`).

## Where things stand (2026-10-28)

- **Session of 2026-10-28: API reference with mkdocstrings** (block 3), plus a fix of
  `Parameter_container.del_parameter()` (it always raised AttributeError). Next in block 3:
  the JOSS paper; the open items of the ASHRAE 140 validation can be interleaved.

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
    (the coil is dry in February in all of them). Possible feature: ADP/bypass-factor dry-coil
    criterion in `DX_unit`.
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
    heavy-mass night-ventilated zone is worth a look). The 640/940 thermostat (linear
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
    rest +0.7 %; GC45b (36 × 4 m) unchanged, ~1 % below. Values 55 → 57/68, hourly
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
  - Other differences to look at: AE101/AE201/AE301/AE401 zone heating load ~3 % above the
    range (3.02 vs 2.93 kW, all references within 0.001); AE101/AE201 heating coil load
    0.3 % below; AE301 coil outlet RH and reheat loads.
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
  - **WD600 ground albedo 0.2 inferred from the reference results** (same Denver weather as
    WD100, vertical diffuse ~19 W/m² higher = 0.2 × 190 × 0.5). To confirm in the Standard.
  - Remaining: vertical beam 0.2–1 % below the range (likely the beam → diffuse rule for
    sun altitude < 3°, largest at Barrow WD400); sky temperature 0.01–0.02 °C above in
    WD300/WD500.
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

- **Editor's lazy Plotly import may hit the same VS Code CSP as the Ajv bug.**
  `src/opensimula/editor/vendor/editor.src.js` does `import(PLOTLY_URL)` (from esm.sh) on
  demand when the 3D view is opened, separate from the Ajv static import that was bundled in
  PR #2. This dynamic import was not implicated in issue #1 (which failed at initial widget
  load), but it fetches from a remote origin the same way the old Ajv import did, so it may
  fail under VS Code's notebook CSP the first time someone opens the 3D view there. Not
  reproduced or confirmed either way — needs checking in an actual VS Code notebook. If it
  does fail, the fix is the same shape as PR #2: vendor `plotly.js-gl3d-dist-min` into the
  esbuild bundle instead of fetching it at runtime (trade-off: bundle size).
- **`Opening.py:79`** — `# TODO: Test surface_type EXTERIOR or INTERIOR` in `check()`: the
  validation that an Opening's `surface_type` is one of the expected values is not
  implemented yet.
- **`HVAC_DX_system.py:14`** — the `spaces` parameter's comment notes it should eventually
  also accept `Air_distribution` and `Energy_load` component types, neither of which exists
  yet in the codebase.

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
- [ ] JOSS paper (multi-author), after items above.
- [ ] Full validation paper (JBPS / Energy and Buildings) and conference talks (IBPSA BS,
  BSO, CYTEF).

### 4. Teaching

- [ ] Open course in marimo notebooks exported to WASM (runs in the browser, no install),
  reusing the CYTEF and HULC course material.
- [ ] Progressive examples gallery (wall → free-floating zone → ideal system → DX → water).
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
