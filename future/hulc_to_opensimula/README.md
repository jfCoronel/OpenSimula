# HULC to OpenSimula (future)

Importer of buildings made with HULC (the Spanish CTE tool, `.ctehexml` files) into
OpenSimula, written for a final degree project (TFG). Not part of the package yet: see
"Future: importer of HULC projects" in `ROADMAP.md`.

- `hulc_to_opensimula.py`: reads the `.ctehexml` and converts its materials, glazings and
  constructions to the dictionary of `Project.read_dict()`.
- `hulc_geometria.py`: geometry (floors, spaces, surfaces, windows), schedules and space
  conditions.
- `ajustes_hulc.py`: adjustments to follow HULC more closely (window U, crack infiltration).
- `parche_opensimula_ff.py`: patch of the form factors of `Space`, written for an older
  version: check whether it is still needed.
- `Demostracion_HULC_OpenSimula_edificio_v2 .ipynb`: demonstration with the test building
  `edificio_pmt_atecyr_sis3.ctehexml`.

The materials missing in a project are read from the HULC catalogue `BDCatalogo.bdc`, which
is not in the repository: copy it from a HULC installation to this folder.
