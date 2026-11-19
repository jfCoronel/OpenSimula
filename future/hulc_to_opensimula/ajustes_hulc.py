"""
Ajustes sobre el diccionario que genera el conversor, para trasladar con más
fidelidad DOS cosas que HULC declara en el .ctehexml y que el conversor no
recoge todavía. NINGUNO cambia un valor de HULC: cambian CÓMO se aplica un
valor que ya viene de HULC.

Se aplican sobre `proyecto` (el dict) DESPUÉS de ctehexml_a_diccionario y ANTES
de pro.read_dict(proyecto).

------------------------------------------------------------------------------
1) u_ventana_hulc(proyecto)                 -> efecto pequeño (~±3 % demanda)
------------------------------------------------------------------------------
Cómo forma HULC la U de una ventana:
  - vidrio (acristalamiento): GLASS-CONDUCTANCE = 3.6 W/m²K   (90 % del hueco)
  - marco: en el GAP "VENTANA" es madera, FRAME-CONDUCT = 2.0 (PORCENTAGE = 10)
  - PERO además:
      * el GAP trae   porcentajeIncrementoU = 10   (incremento por el puente
        térmico del intercalario/separador entre vidrios, y montaje);
      * cada objeto WINDOW individual del .ctehexml trae ya el valor que HULC
        usa de verdad:  FRAME-CONDUCT = 9.223999  (constante en TODAS las
        ventanas; las puertas traen 2.2). Ese 9.224 es el "marco equivalente"
        que agrupa el marco de madera + el puente del intercalario + el
        incremento del 10 %.

El conversor lee el marco del GAP (madera, U = 2.0) y NO lee ni
`porcentajeIncrementoU` ni el `FRAME-CONDUCT` por ventana. Resultado: la U de
ventana en OpenSimula sale por debajo de la de HULC.

Esta función pone la resistencia del marco de ventana en 1/FRAME-CONDUCT con el
valor por ventana del .ctehexml (9.224). Es un dato LITERAL del fichero, no una
aproximación.

Efecto medido (edificio de prueba, con el parche de ff_matrix, cubierta real):
    sin ajuste (marco madera 2.0) ...... U hueco ~3.09   calef 1,12x  refrig 1,20x
    + porcentajeIncrementoU 10% (x1.10) . U hueco ~3.32   calef 1,14x  refrig 1,19x
    + FRAME-CONDUCT 9.224 por ventana ... U hueco ~3.51   calef 1,16x  refrig 1,18x
Es decir: mueve la demanda ~±3 %. No es determinante; el bug de ff_matrix sí.
Se deja como OPCIONAL. Si se aplica, la variante con FRAME-CONDUCT es la fiel.

------------------------------------------------------------------------------
2) infiltracion_crack(proyecto)            -> OPCIONAL (aproximación de método)
------------------------------------------------------------------------------
Las 5 SPACE-CONDITIONS "GESTORIA_x" del .ctehexml traen:
        AIR-CHANGES/HR  = 1
        INF-METHOD      = CRACK-AIR-CHANGE
El VALOR (1 ren/h nominal) es de HULC y NO se toca. Lo que cambia es el MÉTODO:
`CRACK-AIR-CHANGE` significa que HULC (motor DOE-2) NO aplica ese 1 ren/h plano
24 h; lo modula hora a hora con la velocidad de viento y el salto de
temperatura (tiro térmico). El conversor lo aplica plano.

Evidencia en los propios .txt de HULC (columna "Carga de ventilación e
infiltración", P02_E04): media anual -3,67 W/m² (ocupado -7,2 ; no ocupado
-2,5). Con 1 ren/h plano esa columna sería ~el doble. El efectivo anual de HULC
es ~0,55-0,65 ren/h, modulado.

Este ajuste re-aplica el 1 ren/h con la forma DOE-2 más simple:
        factor = velocidad_viento / 4,47
(4,47 m/s es el viento al que DOE-2 deja el factor en 1,0). Para Madrid
(viento medio 2,85 m/s) da una media anual ~0,64 ren/h, coherente con los .txt.

AVISO: los coeficientes exactos de CRACK-AIR-CHANGE no están en el .ctehexml ni
en el .bdc. `V/4,47` es una aproximación del método, no un dato literal. Por eso
es OPCIONAL y va con un flag. El valor nominal (1 ren/h) sigue siendo el de HULC.

Efecto (ya CON el parche de ff_matrix):
    solo parche ff_matrix ................ calef 1,12x   refrig 1,20x
    + u_ventana_hulc + crack ............. calef ~0,95x  refrig ~1,30x
"""

FRAME_CONDUCT_VENTANA = 9.223999   # valor por ventana en el .ctehexml (constante en todas)
FRAME_VENTANA = "VER_Madera de densidad media baja"   # marco del GAP "VENTANA"


def u_ventana_hulc(proyecto, frame_conduct=FRAME_CONDUCT_VENTANA,
                   nombre_frame=FRAME_VENTANA):
    """Pone la resistencia del marco de VENTANA en 1/FRAME-CONDUCT con el valor
    por ventana del .ctehexml (9.224), que ya incluye el puente del intercalario
    y el porcentajeIncrementoU. Dato literal del fichero."""
    n = 0
    for c in proyecto["components"]:
        if c.get("type") == "Frame" and c.get("name") == nombre_frame:
            c["thermal_resistance"] = round(1.0 / frame_conduct, 4)
            n += 1
    print(f"[ajustes_hulc] u_ventana_hulc: marco '{nombre_frame}' "
          f"thermal_resistance = 1/{frame_conduct} = {round(1.0/frame_conduct,4)} "
          f"({n} Frame).")
    return proyecto


def infiltracion_crack(proyecto, v_ref=4.47, tope=3.0, marca_space_type="GESTORIA"):
    """Re-aplica AIR-CHANGES/HR=1 con la forma DOE-2 CRACK-AIR-CHANGE
    (factor = viento / v_ref, acotado a `tope`). Sólo toca los Space_type cuyo
    nombre contiene `marca_space_type` (las 5 GESTORIA)."""
    met = next((c["name"] for c in proyecto["components"]
                if c.get("type") == "File_met"), None)
    if met is None:
        print("[ajustes_hulc] infiltracion_crack: no hay File_met; no se aplica.")
        return proyecto
    n = 0
    for c in proyecto["components"]:
        if c.get("type") == "Space_type" and marca_space_type in c.get("name", ""):
            iv = [x for x in c.get("input_variables", [])
                  if not x.strip().startswith("w ")]
            iv.append(f"w = {met}.wind_speed")
            c["input_variables"] = iv
            # 'i' es el horario INF_GESTORIA (constante 1.0); se mantiene.
            c["infiltration"] = f"min(1.0*i*(w/{v_ref}), {tope})"
            n += 1
    print(f"[ajustes_hulc] infiltracion_crack: {n} Space_type con "
          f"infiltracion = min(1.0*i*(w/{v_ref}), {tope}).")
    return proyecto
