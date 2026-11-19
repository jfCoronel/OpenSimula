"""
Parche para un bug de OpenSimula en el cálculo de factores de forma
(Space._create_ff_matrix), detectado durante la verificación del conversor
HULC -> OpenSimula (TFG).

------------------------------------------------------------------------------
SÍNTOMA
------------------------------------------------------------------------------
En espacios donde un plano (suelo o techo) está partido en varias superficies
-p. ej. la buhardilla P03_E01, cuyo "suelo" son 6 forjados de techo, uno por
oficina de la planta de abajo- la iteración de cierre de la matriz de factores
de forma agota N_MAX_ITER (500) sin converger y deja la suma de esas filas en
~0,707 en vez de 1,0. Además no hay normalización final.

Reproducción (instrumentando la iteración con el edificio de prueba):
    P03_E01 (buhardilla)   -> 6 filas (los techos) suman 0,707
    P02_E06                 -> 2 filas suman 0,76
    P02_E04 (oficina)       -> 3 filas suman 0,956
    P01_E01 (cámara sanit.) -> todas suman 1,000  (no le afecta)

Como el modelo de radiación de onda larga interior de OpenSimula
(Building._create_LW_matrices_) usa esa matriz directamente, ~30 % de la
radiación que emiten esas superficies desaparece (sumidero no físico). En el
edificio de prueba eso enfriaba la buhardilla de 17,7 °C (HULC) a 5,7 °C y
disparaba la demanda del edificio (calefacción ~2x, refrigeración ~0).

------------------------------------------------------------------------------
QUÉ HACE EL PARCHE
------------------------------------------------------------------------------
Envuelve Space._create_ff_matrix. Tras la iteración original, si alguna fila no
suma ~1, recalcula la matriz de ese espacio con un ajuste biproporcional
(Sinkhorn) que impone a la vez:
    - suma de cada fila = 1          (cierre del recinto)
    - reciprocidad  A_i * F_ij = A_j * F_ji
respetando el patrón de superficies que NO se ven (mismo criterio _coplanar
que usa OpenSimula).

No cambia ningún dato del edificio ni de HULC: sólo corrige una violación de
conservación de energía en el cálculo de OpenSimula.

------------------------------------------------------------------------------
VERIFICACIÓN (edificio de prueba, cubierta real, sin aplanar)
------------------------------------------------------------------------------
                          ANTES (bug)      CON PARCHE       HULC
  P03_E01  med/ene/jul     5,7/3,6/9,2     17,4/10,1/27,5   17,7/9,8/27,7
  P02_E06  med/ene/jul     8,6/5,2/13,7    16,5/9,6/25,9    17,6/9,7/27,0
  suma q_lwt de P03_E01    -1207 W          ~0 W            (debe ser 0)
  calefacción edificio     125,4 (1,99x)    70,7 (1,12x)    62,9
  refrigeración edificio     1,7 (0,07x)    28,1 (1,20x)    23,5

------------------------------------------------------------------------------
USO
------------------------------------------------------------------------------
Importar ANTES de crear la Simulation / leer el diccionario, p. ej. justo
después de `import opensimula as osm` en el notebook:

    import opensimula as osm
    import parche_opensimula_ff          # aplica el monkeypatch al importar

Para comprobar que ha hecho efecto, tras pro.check():

    from parche_opensimula_ff import verificar
    verificar(pro)

Para desactivarlo:  parche_opensimula_ff.quitar_parche()
"""

import numpy as np
from opensimula.components.Space import Space

_original_create_ff_matrix = Space._create_ff_matrix
_PARCHE_APLICADO = False


def _patron_vision(space):
    """Matriz booleana n x n: True si las superficies i, j SÍ se ven
    (no coplanares y distintas), con el mismo criterio que OpenSimula."""
    n = len(space.surfaces)
    P = np.zeros((n, n), dtype=bool)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if not space._coplanar(space.surfaces[i], space.sides[i],
                                   space.surfaces[j], space.sides[j]):
                P[i, j] = True
    return P


def _cerrar_matriz(patron, areas, n_iter=300, tol=1e-12):
    """Devuelve ff con filas que suman 1 y reciprocidad A_i F_ij = A_j F_ji,
    partiendo de un reparto proporcional al área vista."""
    areas = np.asarray(areas, dtype=float)
    ff = patron.astype(float) * areas[None, :]     # arranque ~ area(j) vista
    for _ in range(n_iter):
        fila = ff.sum(axis=1, keepdims=True)
        fila[fila < tol] = 1.0
        ff = ff / fila                              # filas -> suma 1
        M = areas[:, None] * ff
        M = 0.5 * (M + M.T)                         # simetriza A_i F_ij
        ff = M / areas[:, None]
        ff[~patron] = 0.0
    fila = ff.sum(axis=1, keepdims=True)
    fila[fila < tol] = 1.0
    return ff / fila


def _create_ff_matrix_parcheado(self):
    _original_create_ff_matrix(self)
    ff = getattr(self, "ff_matrix", None)
    if ff is None or ff.shape[0] == 0:
        return
    if np.all(np.abs(ff.sum(axis=1) - 1.0) <= 1e-3):
        return                                      # este espacio ya estaba bien
    areas = np.array([s.area for s in self.surfaces], dtype=float)
    patron = _patron_vision(self)
    # superficies sin ninguna vista (raro): se dejan como estaban
    if np.any(patron.sum(axis=1) == 0):
        filas_ok = patron.sum(axis=1) > 0
        nueva = ff.copy()
        sub = _cerrar_matriz(patron[np.ix_(filas_ok, filas_ok)], areas[filas_ok])
        nueva[np.ix_(filas_ok, filas_ok)] = sub
        self.ff_matrix = nueva
    else:
        self.ff_matrix = _cerrar_matriz(patron, areas)


def aplicar_parche(verbose=True):
    global _PARCHE_APLICADO
    if _PARCHE_APLICADO:
        return
    Space._create_ff_matrix = _create_ff_matrix_parcheado
    _PARCHE_APLICADO = True
    if verbose:
        print("[parche_opensimula_ff] Space._create_ff_matrix parcheado "
              "(cierre de la matriz de factores de forma).")


def quitar_parche():
    global _PARCHE_APLICADO
    Space._create_ff_matrix = _original_create_ff_matrix
    _PARCHE_APLICADO = False
    print("[parche_opensimula_ff] parche retirado.")


def verificar(project):
    """Imprime, por espacio, min/max de la suma de filas de ff_matrix.
    Con el parche activo todas deben salir 1,000."""
    print(f"{'espacio':14s} {'n_sup':>5s} {'suma_filas min':>15s} {'max':>8s}")
    for comp in project.component_list(comp_type="Space"):
        ff = getattr(comp, "ff_matrix", None)
        if ff is None:
            print(f"{comp.parameter('name').value:14s}   (sin ff_matrix; "
                  f"llama a verificar() DESPUÉS de simulate() o pre_simulation)")
            continue
        s = ff.sum(axis=1)
        print(f"{comp.parameter('name').value:14s} {ff.shape[0]:5d} "
              f"{s.min():15.3f} {s.max():8.3f}")


# Se aplica al importar el módulo.
aplicar_parche()
