"""
hulc_geometria.py
=================

FASE 3 (en desarrollo): extracción de la GEOMETRÍA de un archivo .ctehexml de
HULC: plantas (FLOOR), espacios (SPACE) y superficies/muros (EXTERIOR-WALL,
INTERIOR-WALL, UNDERGROUND-WALL, ROOF), incluyendo el cálculo de coordenadas
3D y orientaciones.

------------------------------------------------------------------------------
POR QUÉ ESTE MÓDULO ES APARTE
------------------------------------------------------------------------------
El parser de las fases 1 y 2 (en hulc_to_opensimula.py) es "plano": recoge
todos los objetos BDL como una lista, sin importar el anidamiento. Para
materiales, vidrios o construcciones eso vale, porque son objetos de nivel
superior independientes.

La geometría, en cambio, es JERÁRQUICA:
    FLOOR (planta)
      └─ SPACE (espacio)
           └─ EXTERIOR-WALL / ROOF / ... (superficies del espacio)
                └─ WINDOW (huecos de esa superficie)

Necesitamos saber qué muro pertenece a qué espacio y a qué planta, así que
aquí usamos un parser que SÍ reconstruye el árbol de anidamiento.

------------------------------------------------------------------------------
EL PROBLEMA GEOMÉTRICO CENTRAL (importante para la memoria del TFG)
------------------------------------------------------------------------------
HULC localiza cada superficie de DOS formas distintas:

1. EXPLÍCITA: la superficie trae X, Y, Z, AZIMUTH, TILT y un POLYGON propio.
   (Ej.: los muros y cubiertas de la planta bajo-cubierta P03.)
   -> Conversión casi directa: ya tenemos posición y orientación.

2. IMPLÍCITA: la superficie solo dice LOCATION = SPACE-Vn, es decir
   "soy el lado n-ésimo del polígono del espacio". (Ej.: muros de P01, P02.)
   -> Hay que CALCULAR su posición y azimut a partir de:
        - el polígono 2D del espacio (lista de vértices),
        - la cota Z de la planta,
        - la altura del espacio.
   Cada lado del polígono (Vn -> Vn+1) define un muro vertical; su azimut se
   obtiene de la dirección de ese lado, y su anchura de la longitud del lado.

Este cálculo 2D->3D es el corazón de la Fase 3.

NOTA: este módulo extrae y calcula la geometría en una estructura intermedia
propia (diccionarios Python con coordenadas y ángulos). El paso final
-traducir esa estructura a los nombres EXACTOS de los componentes de
OpenSimula (Space, Building_surface/Exterior_surface, etc.)- se hará cuando
se confirmen esos nombres con la documentación/el tutor. Así el trabajo de
cálculo (lo difícil) queda hecho y verificable de forma independiente.
"""

import re
import math
import numpy as np


# ===========================================================================
# 1. PARSER JERÁRQUICO DE BDL
# ===========================================================================

_RE_CABECERA = re.compile(r'^(\s*)"([^"]+)"\s*=\s*([A-Z][A-Z0-9\-]*)\s*$')
# OJO con la barra "/": HULC usa claves como AREA/PERSON, LIGHTING-W/AREA,
# EQUIPMENT-W/AREA, AIR-CHANGES/HR o INF-FLOW/AREA. Sin "/" en la clase de
# caracteres esas líneas no casaban y las propiedades se descartaban en
# silencio: justo las que definen las cargas internas de cada espacio.
_RE_PAR = re.compile(r'^\s*([A-Za-z0-9_/\-]+)\s*=\s*(.*?)\s*$')


def _parsear_valor(texto):
    """Convierte la parte derecha de CLAVE = VALOR a un valor Python.
    (Misma lógica que en el módulo principal, replicada para independencia.)"""
    texto = texto.strip()
    if texto.startswith("(") and texto.endswith(")"):
        interior = texto[1:-1]
        return [_parsear_valor(e) for e in interior.split(",") if e.strip() != ""]
    if len(texto) >= 2 and texto.startswith('"') and texto.endswith('"'):
        return texto[1:-1]
    try:
        if re.fullmatch(r"[-+]?\d+", texto):
            return int(texto)
        return float(texto)
    except ValueError:
        return texto


def _unir_listas_multilinea(lineas):
    """Une las listas BDL repartidas en varias líneas en una sola línea.

    HULC parte las listas largas, por ejemplo:

        WEEK-SCHEDULES = ( "HA25_HS0_SS_",
        "HA25_HS1_SS_",
        "HA25_HS2_SS_")

    Sin unirlas, el parser solo veía el primer elemento y descartaba el resto,
    de modo que los horarios (WEEK-SCHEDULES, DAY-SCHEDULES) y las listas de
    valores largas quedaban truncados en silencio.
    """
    unidas = []
    buffer_ = None
    for linea in lineas:
        if buffer_ is not None:
            buffer_ += " " + linea.strip()
            if buffer_.count("(") <= buffer_.count(")"):
                unidas.append(buffer_)
                buffer_ = None
            continue
        # ¿Abre una lista y no la cierra en la misma línea?
        if "=" in linea and linea.count("(") > linea.count(")"):
            buffer_ = linea.rstrip()
        else:
            unidas.append(linea)
    if buffer_ is not None:      # lista sin cerrar al final del archivo
        unidas.append(buffer_)
    return unidas


def parsear_arbol_bdl(texto_bdl):
    """
    Parsea el texto BDL reconstruyendo el árbol de anidamiento por niveles de
    indentación. Devuelve una lista de objetos raíz; cada objeto es un dict:

        {
            "nombre": ...,
            "tipo": ...,
            "props": {clave: valor, ...},
            "hijos": [ ...otros objetos... ],
            "indent": nº de espacios de sangría de su cabecera,
        }

    IMPORTANTE sobre el formato de HULC: cada objeto cierra SU PROPIO bloque de
    propiedades con "..", incluso cuando va a tener "hijos" más indentados
    debajo. Es decir, el cierre ".." NO marca el fin de la jerarquía, solo el
    fin de la lista de propiedades de ese objeto. Por eso el anidamiento entre
    FLOOR -> SPACE -> muro -> WINDOW se decide EXCLUSIVAMENTE por la sangría:
    un objeto es hijo del último objeto previo cuya indentación sea MENOR.

    Las líneas de propiedades (CLAVE = VALOR) se asignan siempre al último
    objeto cuya cabecera se ha leído (el "actual"), hasta que aparece su "..".
    """
    raices = []
    # 'pila' contiene la cadena de ancestros por indentación (no por cierres).
    pila = []
    # 'actual' es el objeto que está recibiendo propiedades ahora mismo.
    actual = None
    recibiendo_props = False

    for linea in _unir_listas_multilinea(texto_bdl.splitlines()):
        if linea.strip() == "":
            continue
        if linea.lstrip().startswith("$"):
            continue

        # El cierre ".." solo significa "fin de las propiedades del objeto
        # actual". No afecta a la jerarquía (que se basa en indentación).
        if linea.strip() == "..":
            recibiendo_props = False
            actual = None
            continue

        m_cab = _RE_CABECERA.match(linea)
        if m_cab:
            indent = len(m_cab.group(1).expandtabs(4))
            obj = {
                "nombre": m_cab.group(2),
                "tipo": m_cab.group(3),
                "props": {},
                "hijos": [],
                "indent": indent,
            }
            # El padre es el último objeto de la pila con indentación MENOR.
            while pila and pila[-1]["indent"] >= indent:
                pila.pop()
            if pila:
                pila[-1]["hijos"].append(obj)
            else:
                raices.append(obj)
            pila.append(obj)
            actual = obj
            recibiendo_props = True
            continue

        m_par = _RE_PAR.match(linea)
        if m_par and actual is not None and recibiendo_props:
            clave = m_par.group(1)
            actual["props"][clave] = _parsear_valor(m_par.group(2))

    return raices


# ===========================================================================
# 2. UTILIDADES GEOMÉTRICAS
# ===========================================================================

def _buscar_objetos(raices, tipo):
    """Recorre el árbol y devuelve TODOS los objetos de un tipo dado,
    estén donde estén en la jerarquía."""
    encontrados = []

    def recorrer(nodo):
        if nodo["tipo"] == tipo:
            encontrados.append(nodo)
        for h in nodo["hijos"]:
            recorrer(h)

    for r in raices:
        recorrer(r)
    return encontrados


def _extraer_polygon(obj_polygon):
    """
    De un objeto POLYGON, extrae la lista de vértices [(x, y), ...].
    Los vértices vienen como V1 = ( x, y ), V2 = ( x, y ), ...
    """
    vertices = []
    i = 1
    while f"V{i}" in obj_polygon["props"]:
        v = obj_polygon["props"][f"V{i}"]
        # v es una lista [x, y]
        if isinstance(v, list) and len(v) >= 2:
            vertices.append((float(v[0]), float(v[1])))
        i += 1
    return vertices


def _sentido_poligono(poligono):
    """
    Devuelve +1 si el polígono está en sentido antihorario (CCW) y -1 si está
    en sentido horario (CW). Se usa el signo del área con la fórmula del
    zapatero. HULC entrega los polígonos de espacio en CCW, pero comprobamos el
    sentido para que el normal exterior de cada lado apunte SIEMPRE hacia fuera.
    """
    s = 0.0
    n = len(poligono)
    for i in range(n):
        x1, y1 = poligono[i]
        x2, y2 = poligono[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return 1.0 if s >= 0 else -1.0


def azimut_de_lado(p1, p2, sentido=1.0):
    """
    Azimut de OpenSimula del muro vertical apoyado en el lado p1->p2 de un
    polígono en planta.

    CONVENCIÓN CORRECTA (verificada en el fuente de OpenSimula 0.7.1,
    Surface.py línea 15): el azimut es el ángulo del NORMAL EXTERIOR de la
    superficie medido desde el eje -Y del edificio, positivo hacia el Este:
        Sur: 0º,  Este: 90º,  Oeste: -90º,  Norte: 180º.

    Para un polígono recorrido en sentido antihorario (CCW, sentido=+1), el
    normal exterior de cada lado apunta a la DERECHA de la dirección de avance:
        d = (dx, dy)  ->  n_ext = (dy, -dx)
    Si el polígono viniera en sentido horario (sentido=-1), el exterior queda a
    la izquierda y se invierte el normal.

    Finalmente:  az = atan2(n_x, -n_y)  reproduce S:0, E:90, O:-90, N:180.

    (Antes se usaba atan2(dy, dx) -> convención E:0, N:90, que NO es la de
    OpenSimula. Este era uno de los errores corregidos.)
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    nx = sentido * dy        # normal exterior x
    ny = sentido * (-dx)     # normal exterior y
    az = math.degrees(math.atan2(nx, -ny))
    if az > 180:
        az -= 360
    elif az <= -180:
        az += 360
    return az


def longitud_lado(p1, p2):
    """Longitud de un lado del polígono (anchura del muro)."""
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def _azimut_alero(x, y, poligono, tol=0.5):
    """
    Para una superficie explícita (muro o cubierta) cuyo X,Y de HULC coincide
    con un vértice del polígono del espacio, localiza el lado que ARRANCA en ese
    vértice y devuelve el azimut de su NORMAL EXTERIOR en la convención de
    OpenSimula (Sur:0, Este:90, Oeste:-90, Norte:180).
    """
    n = len(poligono)
    sentido = _sentido_poligono(poligono)
    # Buscamos el vértice del polígono más cercano a (x, y).
    idx = min(range(n),
              key=lambda i: math.hypot(poligono[i][0] - x, poligono[i][1] - y))
    p1 = poligono[idx]
    p2 = poligono[(idx + 1) % n]
    return azimut_de_lado(p1, p2, sentido)


# ---------------------------------------------------------------------------
# TRANSFORMACIÓN DE SUPERFICIES EXPLÍCITAS: HULC local -> mundo -> OpenSimula
# ---------------------------------------------------------------------------
#
# Este es el núcleo de la corrección de la geometría de las superficies
# EXPLÍCITAS (cubiertas inclinadas, muros y forjados que HULC define con su
# propio polígono local + X, Y, Z + AZIMUTH + TILT).
#
# El error anterior era usar el polígono local de HULC DIRECTAMENTE como
# polígono de superficie de OpenSimula. No vale: HULC y OpenSimula usan
# convenciones DISTINTAS para el sistema de coordenadas local de la superficie,
# así que el mismo polígono 2D se coloca en sitios diferentes. El resultado eran
# faldones y forjados "volando" fuera del edificio.
#
# La solución robusta es en dos pasos:
#   1) Reconstruir las coordenadas 3D REALES (de mundo) de los vértices de la
#      superficie usando la convención de HULC (validada contra los muros del
#      bajocubierta, cuya posición conocemos).
#   2) Re-expresar esos vértices de mundo en los parámetros de OpenSimula
#      (azimuth, altitude, ref_point, x_polygon, y_polygon), invirtiendo la
#      transformación que OpenSimula aplica internamente (Polygon_3D).
# El round-trip se ha verificado con precisión ~1e-2 m en muros y cubiertas.


def _hulc_local_a_mundo(corner, azimuth_hulc, tilt_hulc, poly_local):
    """
    Paso 1: convierte el polígono local 2D de una superficie explícita de HULC
    a coordenadas 3D de mundo.

    Convención de HULC (DOE-2/BDL), decodificada y verificada:
      - corner = (X, Y, Z) de mundo de la superficie (Z ya incluye la planta).
      - AZIMUTH: ángulo del NORMAL EXTERIOR medido desde el Norte (+Y) en sentido
        horario (Norte=0, Este=90, Sur=180, Oeste=270). Con eje X=Este, Y=Norte,
        la proyección horizontal del normal es (sin A, cos A).
      - TILT: ángulo del plano respecto a la horizontal (90=vertical, 0=techo
        plano mirando arriba).
      - El normal de mundo es:
            n = (sin A · sin T,  cos A · sin T,  cos T)
      - El eje x local de HULC es horizontal y equivale al normal girado +90º:
            ux = (-cos A,  sin A,  0)
      - El eje y local sube por el plano:  uy = n × ux.
    Devuelve (lista de vértices 3D np.array, normal np.array).
    """
    import numpy as np
    A = math.radians(azimuth_hulc)
    T = math.radians(tilt_hulc)
    n = np.array([math.sin(A) * math.sin(T),
                  math.cos(A) * math.sin(T),
                  math.cos(T)])
    ux = np.array([-math.cos(A), math.sin(A), 0.0])
    norma = np.linalg.norm(ux)
    if norma > 1e-9:
        ux = ux / norma
    else:
        # Superficie horizontal (tilt 0 o 180): el eje x local es indefinido por
        # el azimut; elegimos +X de mundo como referencia.
        ux = np.array([1.0, 0.0, 0.0])
    uy = np.cross(n, ux)
    C = np.array(corner, dtype=float)
    verts = [C + u * ux + v * uy for (u, v) in poly_local]
    return verts, n


def _mundo_a_opensimula(verts_mundo, normal):
    """
    Paso 2: expresa unos vértices 3D de mundo como una superficie POLYGON de
    OpenSimula, invirtiendo la transformación interna de OpenSimula (Polygon_3D).

    OpenSimula define el normal de la superficie como:
        n = (cos(alt)·sin(az),  -cos(alt)·cos(az),  sin(alt))
    de donde:
        alt = asin(n_z)
        az  = atan2(n_x, -n_y)
    y su sistema local de superficie tiene:
        x_axis = (cos az, sin az, 0)
        y_axis = n × x_axis
    El ref_point se toma en el primer vértice; los demás se proyectan sobre
    (x_axis, y_axis) para obtener el polígono 2D de superficie.

    Devuelve (azimuth, altitude, ref_point[list], x_polygon[list], y_polygon[list]).
    """
    import numpy as np
    n = np.array(normal, dtype=float)
    ln = np.linalg.norm(n)
    if ln > 1e-9:
        n = n / ln
    alt = math.degrees(math.asin(max(-1.0, min(1.0, n[2]))))
    az = math.degrees(math.atan2(n[0], -n[1]))
    azr = math.radians(az)
    x_axis = np.array([math.cos(azr), math.sin(azr), 0.0])
    y_axis = np.cross(n, x_axis)
    origin = np.array(verts_mundo[0], dtype=float)
    x_poly, y_poly = [], []
    for P in verts_mundo:
        d = np.array(P, dtype=float) - origin
        x_poly.append(round(float(d @ x_axis), 4))
        y_poly.append(round(float(d @ y_axis), 4))
    ref_point = [round(float(origin[0]), 4),
                 round(float(origin[1]), 4),
                 round(float(origin[2]), 4)]
    return round(az, 4), round(alt, 4), ref_point, x_poly, y_poly


def superficie_explicita_a_opensimula(x, y, z_mundo, azimuth_hulc,
                                      tilt_hulc, poly_local):
    """
    Envoltorio de los dos pasos: de los datos explícitos de HULC (corner,
    azimuth, tilt, polígono local) a los parámetros de superficie POLYGON de
    OpenSimula (azimuth, altitude, ref_point, x_polygon, y_polygon).

    Es lo que se usa para cubiertas inclinadas, muros y forjados explícitos.
    """
    verts, normal = _hulc_local_a_mundo(
        (x, y, z_mundo), azimuth_hulc, tilt_hulc, poly_local)
    return _mundo_a_opensimula(verts, normal)


# ===========================================================================
# 3. EXTRACCIÓN DE LA GEOMETRÍA EN ESTRUCTURA INTERMEDIA
# ===========================================================================

def extraer_geometria(raices):
    """
    Construye una estructura intermedia con plantas, espacios y superficies,
    calculando coordenadas 3D / orientaciones donde haga falta.

    Devuelve una lista de plantas:
        [
          {
            "nombre": "P02",
            "z": cota Z de la planta,
            "altura": altura de la planta,
            "espacios": [
                {
                  "nombre": "P02_E01",
                  "tipo": "CONDITIONED" / "UNHABITED" / ...,
                  "altura": ...,
                  "poligono": [(x,y), ...],
                  "superficies": [
                      {
                        "nombre": ...,
                        "tipo_hulc": "EXTERIOR-WALL"/"ROOF"/...,
                        "construccion": "MURO EXTERIOR",
                        "localizacion": "explicita"/"implicita",
                        # si explícita:
                        "x","y","z","azimuth","tilt",
                        # si implícita (calculada):
                        "azimuth_calc","ancho_calc","lado",
                        "huecos": [ {nombre, gap, ancho, alto, x, y}, ... ],
                      }, ...
                  ],
                }, ...
            ],
          }, ...
        ]
    """
    # Primero, un índice de todos los POLYGON por nombre (están en el nivel
    # superior del árbol, antes de las plantas).
    poligonos = {}
    for obj in _buscar_objetos(raices, "POLYGON"):
        poligonos[obj["nombre"]] = _extraer_polygon(obj)

    plantas = []
    for floor in _buscar_objetos(raices, "FLOOR"):
        planta = {
            "nombre": floor["nombre"],
            "z": float(floor["props"].get("Z", 0)),
            "altura": float(floor["props"].get("FLOOR-HEIGHT", 0)),
            "espacios": [],
        }

        for space in [h for h in floor["hijos"] if h["tipo"] == "SPACE"]:
            poly_nombre = space["props"].get("POLYGON", "")
            poligono = poligonos.get(poly_nombre, [])

            espacio = {
                "nombre": space["nombre"],
                "tipo": space["props"].get("TYPE", ""),
                # Nombre del objeto SPACE-CONDITIONS que define las cargas
                # internas (ocupación, iluminación, equipos, infiltración) de
                # este espacio. HULC lo declara por espacio; ver
                # _extraer_space_conditions().
                "space_conditions": space["props"].get("SPACE-CONDITIONS", ""),
                "altura": float(space["props"].get("HEIGHT", planta["altura"])),
                "poligono": poligono,
                "superficies": [],
            }

            for muro in space["hijos"]:
                if muro["tipo"] not in (
                    "EXTERIOR-WALL", "INTERIOR-WALL",
                    "UNDERGROUND-WALL", "ROOF",
                ):
                    continue

                props = muro["props"]
                # HULC crea variantes de construcción por absortancia con un
                # nombre tipo "MURO EXTERIOR0.65". La construcción REAL con las
                # capas (objeto LAYERS) es la base, cuyo nombre da el campo
                # CONSTRUCCION_MURO. Usamos esa base para enlazar con el
                # componente Construction que ya extraemos en las fases 1-2.
                construccion = props.get("CONSTRUCCION_MURO",
                                         props.get("CONSTRUCTION", ""))
                sup = {
                    "nombre": muro["nombre"],
                    "tipo_hulc": muro["tipo"],
                    "construccion": construccion,
                    "huecos": [],
                    # Espacio vecino (solo para muros interiores). HULC lo
                    # indica con NEXT-TO. OpenSimula necesita este segundo
                    # espacio para las superficies de tipo INTERIOR.
                    "vecino": props.get("NEXT-TO", ""),
                }

                # ¿Localización explícita o implícita?
                if "AZIMUTH" in props and "TILT" in props:
                    sup["localizacion"] = "explicita"
                    sup["x"] = float(props.get("X", 0))
                    sup["y"] = float(props.get("Y", 0))
                    sup["z"] = float(props.get("Z", 0))
                    sup["azimuth"] = float(props["AZIMUTH"])
                    sup["tilt"] = float(props["TILT"])
                    # Los muros explícitos definen su contorno con un POLYGON
                    # propio en coordenadas locales 2D de la superficie.
                    poly_propio = props.get("POLYGON", "")
                    sup["poligono_local"] = poligonos.get(poly_propio, [])
                else:
                    # Implícita: LOCATION = SPACE-Vn  -> lado n del polígono.
                    sup["localizacion"] = "implicita"
                    location = str(props.get("LOCATION", ""))
                    sup["location"] = location
                    m = re.match(r"SPACE-V(\d+)", location)
                    if m and poligono:
                        n = int(m.group(1))
                        # El lado n va del vértice n al n+1 (con cierre cíclico).
                        p1 = poligono[(n - 1) % len(poligono)]
                        p2 = poligono[n % len(poligono)]
                        sentido = _sentido_poligono(poligono)
                        sup["azimuth_calc"] = round(
                            azimut_de_lado(p1, p2, sentido), 2)
                        sup["ancho_calc"] = round(longitud_lado(p1, p2), 4)
                        sup["lado"] = (p1, p2)
                        sup["tilt"] = 90.0  # muro vertical
                    else:
                        # BOTTOM, TOP, etc. (suelos/techos horizontales).
                        sup["tilt"] = 0.0 if location in ("BOTTOM", "TOP") else None

                # Huecos (WINDOW) que cuelgan de esta superficie.
                for win in muro["hijos"]:
                    if win["tipo"] != "WINDOW":
                        continue
                    wp = win["props"]
                    sup["huecos"].append({
                        "nombre": win["nombre"],
                        "gap": wp.get("GAP", ""),
                        "ancho": float(wp.get("WIDTH", 0)),
                        "alto": float(wp.get("HEIGHT", 0)),
                        "x": float(wp.get("X", 0)),
                        "y": float(wp.get("Y", 0)),
                        # Retranqueo del hueco respecto a la cara exterior del
                        # muro (embrasura). HULC lo da en SETBACK [m]; OpenSimula
                        # lo usa para el autosombreamiento del propio hueco
                        # (Opening.setback). Sin este dato, todo hueco se
                        # modela a haces con la fachada (sin autosombra),
                        # sobrestimando la ganancia solar directa en huecos
                        # retranqueados.
                        "setback": float(wp.get("SETBACK", 0.0)),
                    })

                espacio["superficies"].append(sup)

            planta["espacios"].append(espacio)
        plantas.append(planta)

    return plantas


# ===========================================================================
# 4. CONVERSIÓN DE LA GEOMETRÍA A COMPONENTES DE OPENSIMULA
# ===========================================================================
#
# Mapeo de ángulos HULC -> OpenSimula (deducido de la documentación):
#   - azimuth: HULC usa rango 0..360; OpenSimula usa -180..180.
#       az_os = az_hulc - 360  si az_hulc > 180,  en caso contrario az_hulc.
#   - altitude (OpenSimula) vs tilt (HULC):
#       En HULC, TILT=90 es un muro vertical y TILT=0 una superficie
#       horizontal. En OpenSimula, "altitude" es el ángulo entre el eje Z del
#       edificio y el eje Y de la superficie: para un muro vertical vale 0 y
#       para una superficie horizontal (techo) vale 90 (mirando arriba) o -90.
#       Por tanto:  altitude_os = 90 - tilt_hulc.
#       (Muro vertical: 90-90 = 0.  Techo horizontal: 90-0 = 90.)
#
# Mapeo de tipo de superficie HULC -> surface_type de OpenSimula:
#   EXTERIOR-WALL, ROOF        -> "EXTERIOR"
#   INTERIOR-WALL              -> "INTERIOR"
#   UNDERGROUND-WALL           -> "UNDERGROUND"


def _azimut_a_opensimula(az_hulc):
    """
    Convierte el azimut de ORIENTACIÓN de HULC al azimut de OpenSimula, para el
    caso de respaldo en que no hay polígono del espacio del que sacar el normal.

    HULC mide el azimut desde el Norte en sentido horario (Norte=0, Este=90,
    Sur=180, Oeste=270). OpenSimula lo mide desde el eje -Y (Sur) positivo hacia
    el Este (Sur=0, Este=90, Oeste=-90, Norte=180). La relación es:
        az_os = 180 - az_hulc      (y se normaliza a (-180, 180]).
    """
    az = 180.0 - (az_hulc % 360.0)
    if az > 180.0:
        az -= 360.0
    elif az <= -180.0:
        az += 360.0
    return round(az, 4)


def _tilt_a_altitude(tilt_hulc):
    """Convierte el TILT de HULC al 'altitude' de OpenSimula (= 90 - tilt)."""
    if tilt_hulc is None:
        return 0.0
    return round(90.0 - tilt_hulc, 4)


_TIPO_SUPERFICIE = {
    "EXTERIOR-WALL": "EXTERIOR",
    "ROOF": "EXTERIOR",
    "INTERIOR-WALL": "INTERIOR",
    "UNDERGROUND-WALL": "UNDERGROUND",
}


def _componentes_horario_cte():
    """
    Crea los componentes de horario (schedules) del perfil residencial del CTE,
    según los componentes Day_schedule, Week_schedule y Year_schedule de
    OpenSimula. Devuelve la lista de componentes de horario.

    RESPALDO: solo gobierna las cargas de un espacio que no traiga su propio
    SCHEDULE-PD en el .ctehexml. Con archivos completos de HULC (los dos
    edificios de prueba) no llega a activarse; se mantiene para no romper la
    conversión de un .ctehexml futuro incompleto -degradaría con cuidado en vez
    de fallar-.

    El perfil residencial del CTE define una variación horaria de las cargas
    internas (ocupación, iluminación, equipos) y de las consignas. Aquí se
    implementan perfiles simplificados pero representativos:

    - Cargas internas (factor 0..1 que multiplica la densidad): más altas por
      la tarde-noche (gente en casa) y más bajas a media mañana (gente fuera).
    - Consigna de calefacción: 17 °C por la noche (0-7 h) y 20 °C el resto.
    - Consigna de refrigeración: 27 °C por la noche y 25 °C de día (solo afecta
      en verano).

    Tiempos en segundos desde medianoche: 7 h = 25200 s, 15 h = 54000 s,
    23 h = 82800 s.

    NOTA: estos perfiles son una aproximación al perfil normativo del CTE.
    Los valores exactos hora a hora están en el documento de condiciones
    operacionales del CTE y pueden afinarse con el tutor.
    """
    comps = []

    # --- Perfil de cargas internas (factor 0..1) ---
    # Día tipo: noche y tarde alto (1.0), mañana-mediodía bajo (0.5).
    comps.append({
        "type": "Day_schedule",
        "name": "dia_cargas",
        "time_steps": [25200, 28800, 28800],   # 7h + 8h + 8h, resto (1h) auto
        "values": [1.0, 0.5, 1.0, 0.5],         # 0-7:1, 7-15:0.5, 15-23:1, 23-24:0.5
        "interpolation": "STEP",
    })
    comps.append({
        "type": "Week_schedule",
        "name": "semana_cargas",
        "days_schedules": ["dia_cargas"],       # mismo perfil todos los días
    })
    comps.append({
        "type": "Year_schedule",
        "name": "anual_cargas",
        "periods": [],                          # un solo periodo todo el año
        "weeks_schedules": ["semana_cargas"],
    })

    # --- Consigna de calefacción (°C) ---
    comps.append({
        "type": "Day_schedule",
        "name": "dia_calef",
        "time_steps": [25200, 57600],           # 7h + 16h, resto (1h) auto
        "values": [17, 20, 17],                 # noche 17, día 20, noche 17
        "interpolation": "STEP",
    })
    comps.append({
        "type": "Week_schedule",
        "name": "semana_calef",
        "days_schedules": ["dia_calef"],
    })
    comps.append({
        "type": "Year_schedule",
        "name": "anual_calef",
        "periods": [],
        "weeks_schedules": ["semana_calef"],
    })

    # --- Consigna de refrigeración (°C) ---
    comps.append({
        "type": "Day_schedule",
        "name": "dia_refrig",
        "time_steps": [25200, 57600],           # 7h + 16h, resto (1h) auto
        "values": [27, 25, 27],                 # noche 27, día 25, noche 27
        "interpolation": "STEP",
    })
    comps.append({
        "type": "Week_schedule",
        "name": "semana_refrig",
        "days_schedules": ["dia_refrig"],
    })
    comps.append({
        "type": "Year_schedule",
        "name": "anual_refrig",
        "periods": [],
        "weeks_schedules": ["semana_refrig"],
    })

    # --- Perfil de VENTILACIÓN (factor 0..1 sobre el caudal higiénico) ---
    # El CTE no aplica el caudal de ventilación plano: lo modula a lo largo
    # del día (más alto con ocupación, reducido de madrugada). Este factor
    # multiplica las renovaciones higiénicas en el Space_type.
    comps.append({
        "type": "Day_schedule",
        "name": "dia_ventila",
        "time_steps": [25200, 57600],   # 7h (25200s) + 16h (57600s), resto auto
        "values": [0.5, 1.0, 0.5],       # noche 50%, día 100%, noche 50%
        "interpolation": "STEP",
    })
    comps.append({
        "type": "Week_schedule",
        "name": "semana_ventila",
        "days_schedules": ["dia_ventila"],
    })
    comps.append({
        "type": "Year_schedule",
        "name": "anual_ventila",
        "periods": [],
        "weeks_schedules": ["semana_ventila"],
    })

    return comps


def _traducir_horarios(raices, nombres_schedules):
    """Traduce los horarios de HULC (BDL) a componentes de OpenSimula.

    HULC y OpenSimula usan la misma jerarquía de tres niveles, así que la
    traducción es directa:

        SCHEDULE-PD       -> Year_schedule    (periodos estacionales)
        WEEK-SCHEDULE-PD  -> Week_schedule    (7 días, de lunes a domingo)
        DAY-SCHEDULE-PD   -> Day_schedule     (24 valores horarios)

    Detalles del formato:
      * SCHEDULE-PD lista MONTH/DAY con la fecha FINAL de cada periodo y una
        WEEK-SCHEDULES por periodo. Year_schedule espera los cortes como
        "DD/MM" y una semana más que periodos, así que se traduce quitando el
        último corte (31/12, implícito).
      * WEEK-SCHEDULE-PD ya viene en orden lunes..domingo, igual que
        Week_schedule (que indexa con date.weekday(), 0 = lunes).
      * DAY-SCHEDULE-PD da 24 valores horarios. Day_schedule exige
        len(time_steps) == len(values) - 1, de ahí 23 pasos de 3600 s.

    'nombres_schedules' son los SCHEDULE-PD que hay que traducir (los que
    referencian las SPACE-CONDITIONS). Se arrastran las semanas y días que
    necesiten. Devuelve (componentes, mapa {nombre_bdl: nombre_opensimula}).
    """
    dias = {o["nombre"]: o for o in _buscar_objetos(raices, "DAY-SCHEDULE-PD")}
    semanas = {o["nombre"]: o for o in _buscar_objetos(raices, "WEEK-SCHEDULE-PD")}
    anuales = {o["nombre"]: o for o in _buscar_objetos(raices, "SCHEDULE-PD")}

    componentes = []
    hechos = set()
    mapa = {}

    def slug(nombre, prefijo):
        # Nombres seguros para OpenSimula (sin espacios ni caracteres raros).
        limpio = re.sub(r"[^A-Za-z0-9_]+", "_", nombre).strip("_")
        return f"{prefijo}_{limpio}"

    def emitir_dia(nombre):
        clave = ("dia", nombre)
        if clave in hechos:
            return slug(nombre, "dia")
        obj = dias.get(nombre)
        if obj is None:
            return None
        vals = obj["props"].get("VALUES", [])
        vals = [vals] if not isinstance(vals, list) else list(vals)
        if not vals:
            return None
        componentes.append({
            "type": "Day_schedule",
            "name": slug(nombre, "dia"),
            # 24 valores horarios -> 23 pasos de una hora (len(values) - 1).
            "time_steps": [3600] * (len(vals) - 1),
            "values": [float(v) for v in vals],
            "interpolation": "STEP",
        })
        hechos.add(clave)
        return slug(nombre, "dia")

    def emitir_semana(nombre):
        clave = ("sem", nombre)
        if clave in hechos:
            return slug(nombre, "sem")
        obj = semanas.get(nombre)
        if obj is None:
            return None
        ds = obj["props"].get("DAY-SCHEDULES", [])
        ds = [ds] if not isinstance(ds, list) else list(ds)
        nombres_dias = [emitir_dia(d) for d in ds]
        nombres_dias = [d for d in nombres_dias if d]
        if not nombres_dias:
            return None
        # Week_schedule admite 1 o 7 días exactamente.
        if len(nombres_dias) not in (1, 7):
            nombres_dias = (nombres_dias + [nombres_dias[-1]] * 7)[:7]
        componentes.append({
            "type": "Week_schedule",
            "name": slug(nombre, "sem"),
            "days_schedules": nombres_dias,
        })
        hechos.add(clave)
        return slug(nombre, "sem")

    for nombre in nombres_schedules:
        obj = anuales.get(nombre)
        if obj is None:
            continue
        ws = obj["props"].get("WEEK-SCHEDULES", [])
        ws = [ws] if not isinstance(ws, list) else list(ws)
        meses = obj["props"].get("MONTH", [])
        dias_mes = obj["props"].get("DAY", [])
        meses = [meses] if not isinstance(meses, list) else list(meses)
        dias_mes = [dias_mes] if not isinstance(dias_mes, list) else list(dias_mes)

        nombres_sem = [emitir_semana(w) for w in ws]
        nombres_sem = [s for s in nombres_sem if s]
        if not nombres_sem:
            continue

        # HULC da la fecha FINAL de cada periodo; el último es 31/12 y sobra,
        # porque Year_schedule necesita una semana más que cortes.
        periodos = []
        for mes, dia in list(zip(meses, dias_mes))[:-1]:
            periodos.append(f"{int(dia):02d}/{int(mes):02d}")
        # Coherencia: nº de semanas = nº de periodos + 1.
        if len(nombres_sem) != len(periodos) + 1:
            periodos = periodos[:max(0, len(nombres_sem) - 1)]
            nombres_sem = nombres_sem[:len(periodos) + 1]

        componentes.append({
            "type": "Year_schedule",
            "name": slug(nombre, "anual"),
            "periods": periodos,
            "weeks_schedules": nombres_sem,
        })
        mapa[nombre] = slug(nombre, "anual")

    return componentes, mapa


def _extraer_system_conditions(raices):
    """Extrae las condiciones de los sistemas (SYSTEM-CONDITIONS) de HULC.

    Cada espacio acondicionado referencia un SYSTEM-CONDITIONS que define:

        HEAT-TEMP-SCH    = "Horario-Calefaccion-t"   consigna de calefacción
        COOL-TEMP-SCH    = "Horario-Refrigeracion-t" consigna de refrigeración
        HEATING-SCHEDULE = "FUN_GESTORIA"            cuándo funciona el sistema
        COOLING-SCHEDULE = "FUN_GESTORIA"
        SEASON-SCH       = "SSHA"                    temporada (1=inv, 0=ver)
        OUTSIDE-AIR-FLOW = 0                         caudal de aire exterior

    SEASON-SCH es el conmutador de temporada: vale 1 cuando la calefacción está
    disponible (invierno) y 0 cuando lo está la refrigeración (verano). Sin él,
    un sistema con ambas consignas activas todo el año calienta a 20 °C también
    en verano, y el espacio nunca llega a los 25 °C de la consigna de frío: la
    demanda de refrigeración sale casi nula.
    """
    conds = {}
    for obj in _buscar_objetos(raices, "SYSTEM-CONDITIONS"):
        p = obj["props"]
        try:
            oaf = float(p.get("OUTSIDE-AIR-FLOW", 0.0))
        except (TypeError, ValueError):
            oaf = 0.0
        conds[obj["nombre"]] = {
            "heat_temp_sch": p.get("HEAT-TEMP-SCH", ""),
            "cool_temp_sch": p.get("COOL-TEMP-SCH", ""),
            "heating_schedule": p.get("HEATING-SCHEDULE", ""),
            "cooling_schedule": p.get("COOLING-SCHEDULE", ""),
            "season_sch": p.get("SEASON-SCH", ""),
            "outside_air_flow": oaf,
            "tipo": p.get("TYPE", ""),
        }
    return conds


def _extraer_system_conditions_por_espacio(raices):
    """Devuelve {nombre_espacio: nombre_system_conditions}."""
    mapa = {}
    for obj in _buscar_objetos(raices, "SPACE"):
        sc = obj["props"].get("SYSTEM-CONDITIONS")
        if sc:
            mapa[obj["nombre"]] = sc
    return mapa


def _extraer_space_conditions(raices):
    """Extrae las cargas internas reales que HULC declara en el .ctehexml.

    HULC define las condiciones operacionales de cada espacio en objetos
    SPACE-CONDITIONS, y cada SPACE las referencia por nombre:

        "P02_E01" = SPACE ... SPACE-CONDITIONS = "GESTORIA_1"

        "GESTORIA_1" = SPACE-CONDITIONS
            AREA/PERSON       = 10        (m²/persona -> 0.1 pers/m²)
            PEOPLE-HG-SENS    = 74.2      (W sensibles por persona)
            PEOPLE-HG-LAT     = 45.42     (W latentes por persona)
            LIGHTING-W/AREA   = 7.4       (W/m² de iluminación)
            EQUIPMENT-W/AREA  = 4.5       (W/m² de equipos)
            AIR-CHANGES/HR    = 1         (ren/h de infiltración)
            ...

    Devuelve {nombre_condiciones: {parámetros ya convertidos a OpenSimula}}.
    Los espacios no habitables suelen apuntar a unas condiciones con todo a 0
    (p. ej. "NIVEL_ESTANQUEIDAD_1"), lo que se traduce solo.
    """
    conds = {}
    for obj in _buscar_objetos(raices, "SPACE-CONDITIONS"):
        p = obj["props"]

        def num(clave, defecto=0.0):
            v = p.get(clave)
            if v is None:
                return defecto
            try:
                return float(v)
            except (TypeError, ValueError):
                return defecto

        area_persona = num("AREA/PERSON", 0.0)
        # HULC da m²/persona; OpenSimula quiere personas/m².
        people_density = (1.0 / area_persona) if area_persona > 0 else 0.0

        conds[obj["nombre"]] = {
            "people_density": round(people_density, 4),
            "people_sensible": num("PEOPLE-HG-SENS", 70.0),
            "people_latent": num("PEOPLE-HG-LAT", 35.0),
            "light_density": num("LIGHTING-W/AREA", 0.0),
            "other_gains_density": num("EQUIPMENT-W/AREA", 0.0),
            # Fracción radiante: HULC da la fracción CONVECTIVA en *-SPLIT-CR.
            "people_radiant_fraction": round(1.0 - num("PEOPLE-SPLIT-CR", 0.4), 4),
            "other_gains_radiant_fraction": round(
                1.0 - num("EQUIPMENT-SPLIT-CR", 0.5), 4),
            # LIGHTING-SPLIT-CR: fracción CONVECTIVA de la iluminación (0.5 en
            # este proyecto) -> light_radiant_fraction = 1 - eso. Antes no se
            # leía y se dejaba el valor por defecto de OpenSimula (0.6).
            "light_radiant_fraction": round(1.0 - num("LIGHTING-SPLIT-CR", 0.4), 4),
            # EQUIP-SENSIBLE / EQUIP-LATENT: reparto sensible/latente de la
            # carga de equipos, en TANTO POR CIENTO que deben sumar 100 (p.ej.
            # 90/10). other_gains_density ya lleva el total (EQUIPMENT-W/AREA);
            # other_gains_latent_fraction es la fracción de ESE total que es
            # latente. Antes no se leía y se dejaba 0.0 (todo sensible) por
            # defecto de OpenSimula.
            "other_gains_latent_fraction": round(
                num("EQUIP-LATENT", 0.0)
                / max(num("EQUIP-SENSIBLE", 100.0) + num("EQUIP-LATENT", 0.0), 1e-9),
                4) if ("EQUIP-LATENT" in p or "EQUIP-SENSIBLE" in p) else 0.0,
            # Infiltración: preferimos AIR-CHANGES/HR (ren/h), que es
            # directamente lo que pide OpenSimula. Si no está, miramos
            # INF-FLOW/AREA (caudal por área, otro método de HULC para
            # definir infiltración -habitual en espacios no habitables como
            # cámaras sanitarias, INF-METHOD=AIR-CHANGE con INF-FLOW/AREA en
            # vez de AIR-CHANGES/HR-). Sin el volumen del espacio no podemos
            # convertir un valor de INF-FLOW/AREA distinto de cero a ren/h con
            # precisión, pero el caso 0 no necesita conversión: sigue siendo
            # 0 ren/h. Si ninguno de los dos está, NO hay dato real de HULC:
            # se marca tiene_air_changes=False para que el llamante sepa que
            # va a usar un valor por defecto (no inventado silenciosamente).
            "infiltration": (num("AIR-CHANGES/HR", 0.0) if "AIR-CHANGES/HR" in p
                              else 0.0),
            "tiene_air_changes": (
                "AIR-CHANGES/HR" in p
                or ("INF-FLOW/AREA" in p and num("INF-FLOW/AREA", None) == 0.0)
            ),
            # Masa de mobiliario (inercia térmica). HULC da FURN-WEIGHT en
            # kg/m² de superficie CUBIERTA por mobiliario, y FURN-FRACTION es
            # la fracción del suelo total cubierta por ese mobiliario.
            # Space.furniture_weight de OpenSimula es kg/m² de SUELO TOTAL del
            # espacio, así que hay que multiplicar ambos.
            "furn_weight": num("FURN-WEIGHT", 0.0),
            "furn_fraction": num("FURN-FRACTION", 0.0),
            # Método de infiltración de HULC. Importa para saber cómo tratar
            # AIR-CHANGES/HR: con INF-METHOD = AIR-CHANGE es el caudal aplicado
            # tal cual; con INF-METHOD = CRACK / CRACK-AIR-CHANGE ese valor es
            # una REFERENCIA a presión de ensayo (tipo n50), y el motor de HULC
            # (DOE-2) lo reduce con el modelo de rendijas hasta la infiltración
            # media real (~0,1-0,4 ren/h en vivienda estándar). Ver
            # geometria_a_componentes().
            "inf_method": p.get("INF-METHOD", ""),
            # Horarios que HULC asocia a cada carga (objetos SCHEDULE-PD).
            "people_schedule": p.get("PEOPLE-SCHEDULE", ""),
            "lighting_schedule": p.get("LIGHTING-SCHEDULE", ""),
            "equip_schedule": p.get("EQUIP-SCHEDULE", ""),
            "inf_schedule": p.get("INF-SCHEDULE", ""),
        }
    return conds


def _nombre_space_type(nombre_cond):
    """Nombre del Space_type de OpenSimula para unas condiciones de HULC."""
    return f"Uso_{nombre_cond}"


def _corregir_orden_spaces_forjados(componentes):
    """Reordena la lista "spaces" de los forjados INTERIOR horizontales.

    OpenSimula asigna el "side" de cada espacio por su POSICIÓN en "spaces":
    spaces[0] -> side 0 (la cara hacia la que apunta la normal exterior, la que
    marca "altitude") y spaces[1] -> side 1 (la cara opuesta).
    Surface.orientation_angle("altitude", side) devuelve +altitude para side=0 y
    -altitude para side=1, y Space._create_dist_vectors considera SUELO de un
    espacio aquella superficie cuyo orientation_angle, visto por ese espacio,
    vale +90.

    De ahí la regla para un forjado horizontal entre dos plantas:
        altitude = -90 (cara 0 hacia ABAJO)  -> spaces = [abajo, arriba]
        altitude = +90 (cara 0 hacia ARRIBA) -> spaces = [arriba, abajo]

    Así, el espacio para el que el forjado es su SUELO siempre lo ve como +90 y
    su floor_area se detecta bien. Sin esto, la radiación solar directa no se
    concentra en el suelo, sino que se reparte por toda la envolvente.

    Quién está arriba y quién abajo se deduce de la GEOMETRÍA: se estima la cota
    del suelo de cada espacio como la Z mínima de sus superficies, y el espacio
    cuyo suelo coincide con la cota del forjado es el de arriba.
    """
    z_suelo = {}
    for c in componentes:
        if c.get("type") != "Building_surface":
            continue
        ref = c.get("ref_point")
        if not ref:
            continue
        z = ref[2]
        espacios = c.get("spaces")
        espacios = espacios if isinstance(espacios, list) else [espacios]
        for e in espacios:
            if e is None:
                continue
            z_suelo[e] = min(z_suelo.get(e, float("inf")), z)

    for c in componentes:
        if (c.get("type") != "Building_surface"
                or c.get("surface_type") != "INTERIOR"):
            continue
        alt = c.get("altitude")
        if alt not in (90.0, -90.0):
            continue                      # solo forjados horizontales
        sp = c.get("spaces")
        if not isinstance(sp, list) or len(sp) != 2 or sp[0] == sp[1]:
            continue                      # medianeras adiabáticas: no aplica
        ref = c.get("ref_point")
        if not ref:
            continue
        z_forjado = ref[2]
        a, b = sp
        if a not in z_suelo or b not in z_suelo:
            continue
        # El espacio cuyo SUELO está a la cota del forjado es el de arriba.
        if abs(z_suelo[a] - z_forjado) <= abs(z_suelo[b] - z_forjado):
            arriba, abajo = a, b
        else:
            arriba, abajo = b, a
        c["spaces"] = [abajo, arriba] if alt == -90.0 else [arriba, abajo]


def geometria_a_componentes(plantas, nombre_edificio="Edificio",
                            incluir_hvac=False,
                            heating_setpoint="20", cooling_setpoint="25",
                            infiltracion=None, carga_interna_W_m2=4.4,
                            ventilacion_renh=None,
                            caudal_impulsion_m3h=None, inf_flow=None,
                            pct_air_changes=None,
                            n50_medido=None, recuperador_calor=0.0,
                            usar_horarios_cte=False,
                            aplanar_cubierta=False,
                            muros_verticales_underground=True,
                            space_conditions=None,
                            horarios_map=None,
                            componentes_horarios=None,
                            system_conditions=None,
                            system_conditions_por_espacio=None,
                            incluir_unconditioned=False,
                            espesores_construcciones=None):
    """
    Traduce la estructura intermedia de geometría a una lista de componentes
    de OpenSimula: un Building, los Space y los Building_surface (con sus
    Opening colgando).

    infiltracion / ventilacion_renh : ren/h. Si se dejan en None (por defecto),
    se calculan a partir de los datos del .ctehexml que pasa el llamante,
    reproduciendo el desglose del informe HE-1 de HULC:
      - ventilacion_renh = INF-FLOW ponderado por PERCENTAGE-AIR-CHANGES entre
        el volumen habitable, es decir
        (p0*|INF-FLOW[0]| + p1*|INF-FLOW[1]|) / (p0+p1) / V,
        con (p0, p1) = pct_air_changes (horas/día a caudal base y a caudal
        punta). Si no hay INF-FLOW se usa caudal_impulsion_m3h / V.
      - infiltracion = n50_medido/20 si hay ensayo de permeabilidad; si no, el
        AIR-CHANGES/HR que la SPACE-CONDITIONS declara con INF-METHOD=CRACK es
        la referencia n50, así que infiltracion = AIR-CHANGES/HR / 20; si
        tampoco, 0,33 ren/h con aviso. Pasar un número fuerza ese valor.
    Solo afecta a los Space_type con INF-METHOD = CRACK (los que HULC no aplica
    literal); para AIR-CHANGE / CRACK-AIR-CHANGE se usa el AIR-CHANGES/HR del
    archivo tal cual.

    aplanar_cubierta : NO usar en la conversión normal, falsea la geometría.
    Sustituye la cubierta inclinada real por un techo plano equivalente; es
    solo una herramienta de diagnóstico (aislar el patrón del fallo de factores
    de forma de OpenSimula). En producción la cubierta se traslada tal como la
    define HULC.

    NOTA sobre el ref_point de muros implícitos:
    Para los muros con coordenadas explícitas (HULC ya da X, Y, Z) usamos ese
    punto directamente. Para los muros implícitos calculamos la esquina
    inferior del lado del polígono (el primer vértice del lado) a la cota Z de
    la planta. El criterio exacto de "esquina inferior IZQUIERDA vista desde
    fuera" depende de la orientación del eje X de la superficie en OpenSimula;
    se deja preparado para ajustar con las figuras de la documentación.
    """
    componentes = []

    # --- Building ---
    componentes.append({
        "type": "Building",
        "name": nombre_edificio,
        "azimuth": 0,
        "ref_point": [0, 0, 0],
    })

    # --- Horarios reales de HULC ---
    # Si se han traducido los SCHEDULE-PD del .ctehexml, se añaden aquí para
    # que los Space_type puedan referenciarlos.
    if componentes_horarios:
        componentes.extend(componentes_horarios)

    # --- Volumen por SPACE-CONDITIONS (para pasar de m3/h a ren/h) ---
    # Cada SPACE-CONDITIONS se aplica a un conjunto de espacios; el caudal de
    # infiltración/ventilación que HULC da en m3/h se reparte sobre el volumen
    # de ESOS espacios. Se calcula aquí, antes de los Space_type, con la misma
    # fórmula (area del polígono x altura) que luego usa cada Space.
    _vol_por_cond = {}
    _vol_total = 0.0
    for _pl in plantas:
        for _e in _pl["espacios"]:
            _v = (_area_poligono(_e["poligono"]) if _e["poligono"] else 1.0) * _e["altura"]
            _vol_total += _v
            _c = _e.get("space_conditions", "")
            _vol_por_cond[_c] = _vol_por_cond.get(_c, 0.0) + _v

    # Caudal de ventilación efectivo (m3/h): INF-FLOW ponderado por
    # PERCENTAGE-AIR-CHANGES (horas/día a caudal base y a caudal punta). Con
    # INF-FLOW = (-129.6, -309.6) y (23, 1) da (23*129.6 + 1*309.6)/24 = 137.1
    # m3/h, que dividido por el volumen habitable reproduce EXACTAMENTE la
    # "Ventilación en renovaciones/hora" del informe HE-1 de HULC.
    _vent_m3h = None
    if inf_flow:
        _if = [abs(float(x)) for x in (inf_flow if isinstance(inf_flow, (list, tuple)) else [inf_flow])]
        _p = [float(x) for x in (pct_air_changes or [])] or [1.0] * len(_if)
        _p = (_p + [0.0] * len(_if))[:len(_if)]
        _sp = sum(_p) or 1.0
        _vent_m3h = sum(w * q for w, q in zip(_p, _if)) / _sp
    elif caudal_impulsion_m3h:
        _vent_m3h = float(caudal_impulsion_m3h)

    def _resolver_inf_vent(nombre_cond, ac_ref=None):
        """(infiltracion, ventilacion, origen) en ren/h para una
        SPACE-CONDITIONS. Usa los valores forzados por el llamante si los hay;
        si no, los deriva del .ctehexml reproduciendo el desglose del HE-1.
        ac_ref = AIR-CHANGES/HR que declara esa SPACE-CONDITIONS (la referencia
        n50 cuando INF-METHOD = CRACK)."""
        V = _vol_por_cond.get(nombre_cond) or _vol_total or 1.0
        if ventilacion_renh is not None:
            vent = float(ventilacion_renh)
        elif _vent_m3h is not None:
            # El recuperador de calor (SYSTEM-CONDITIONS.RECOV-EFF) rebaja la
            # carga sensible del aire de ventilación; la infiltración no pasa
            # por él. En los .ctehexml de ejemplo RECOV-EFF = 0.
            eta = max(0.0, min(float(recuperador_calor or 0.0), 0.95))
            vent = round(_vent_m3h / V * (1.0 - eta), 4)
        else:
            vent = 0.0
        if infiltracion is not None:
            inf = float(infiltracion)
            origen = "valor forzado por el llamante"
        elif n50_medido and float(n50_medido) > 0:
            inf = round(float(n50_medido) / 20.0, 4)
            origen = f"n50 medido {n50_medido} / 20"
        elif ac_ref and float(ac_ref) > 0:
            inf = round(float(ac_ref) / 20.0, 4)
            origen = f"AIR-CHANGES/HR {ac_ref} / 20 (referencia n50 de INF-METHOD=CRACK)"
        else:
            inf = 0.33
            origen = ("0,33 ren/h (referencia CTE; sin ensayo ni AIR-CHANGES/HR: "
                      "confirmar con el informe HE-1 de HULC)")
        return inf, vent, origen

    # --- Space_type: cargas internas ---
    # Cada Space de OpenSimula necesita un Space_type que defina sus cargas
    # internas (ocupación, iluminación, equipos, infiltración).
    #
    # HULC ya trae esta información en el .ctehexml: cada SPACE referencia un
    # objeto SPACE-CONDITIONS con los valores reales (AREA/PERSON,
    # LIGHTING-W/AREA, EQUIPMENT-W/AREA, AIR-CHANGES/HR...). Si se han
    # extraído (parámetro space_conditions), se genera un Space_type por cada
    # uno con esos valores; así el modelo usa las mismas cargas que HULC en vez
    # de un perfil inventado.
    #
    # RESPALDO (casi nunca se activa con datos reales): si un .ctehexml no trae
    # SPACE-CONDITIONS, se cae a un Space_type genérico gobernado por estos
    # parámetros, cuyos valores por defecto (infiltracion="0.33",
    # carga_interna_W_m2=4.4) solo entran en juego en ese caso. Con los dos
    # edificios de prueba nunca llega a usarse.
    #  - infiltracion: renovaciones de aire por hora (ren/h). NO es el n50
    #    (permeabilidad a 50 Pa); la infiltración media se estima como
    #    i_media ≈ n50/20. (También se usa, con el valor que pase el llamante,
    #    en la rama INF-METHOD=CRACK de abajo.)
    #  - ventilacion_renh: ventilación higiénica (HS3) añadida como pérdida.
    #  - carga_interna_W_m2: densidad de cargas internas (iluminación + otros),
    #    repartida entre light_density y other_gains_density.
    nombre_space_type = "Tipo_residencial_generico"   # respaldo
    mitad_carga = round(carga_interna_W_m2 / 2.0, 3)

    space_types_generados = {}     # nombre_condiciones -> nombre del Space_type
    if space_conditions:
        for nombre_cond, c in space_conditions.items():
            st_name = _nombre_space_type(nombre_cond)
            # Infiltración. HULC declara AIR-CHANGES/HR junto a INF-METHOD:
            #   - INF-METHOD = AIR-CHANGE       -> AIR-CHANGES/HR es el caudal
            #     aplicado tal cual (se usa el valor del archivo).
            #   - INF-METHOD = CRACK-AIR-CHANGE -> híbrido: rendijas + un caudal
            #     de aire tipo air-change. Aquí se mantiene el valor del archivo
            #     (el nombre del método incluye "AIR-CHANGE"), pero conviene
            #     saber que HULC lo modula por viento/tiro y el efectivo anual
            #     suele ser menor (~0,6 en vez de 1,0).
            #   - INF-METHOD = CRACK            -> AIR-CHANGES/HR es SOLO una
            #     referencia a presión de ensayo (tipo n50). El motor de HULC
            #     lo reduce con el modelo de rendijas hasta la infiltración
            #     media real. Tomarlo literal es un error grave (una vivienda
            #     con AIR-CHANGES/HR = 4 se simularía a 4 ren/h). En ese caso
            #     NO se usa el valor del archivo: se usa la infiltración +
            #     ventilación derivadas de <valorImpulsionAire>/INF-FLOW/n50
            #     (o forzadas por el llamante) -> _resolver_inf_vent().
            inf_method = str(c.get("inf_method", "")).upper().replace(" ", "")
            crack_referencia = (inf_method == "CRACK")
            _ac_ref = c.get("infiltration") if c.get("tiene_air_changes") else None
            if c.get("tiene_air_changes") and not crack_referencia:
                infil = c["infiltration"]
            elif crack_referencia:
                inf_r, vent_r, origen_r = _resolver_inf_vent(nombre_cond, _ac_ref)
                infil = round(inf_r + vent_r, 4)
                if c.get("tiene_air_changes"):
                    _rec = (f" (con recuperador η={float(recuperador_calor):.2f})"
                            if recuperador_calor else "")
                    print(f"[hulc_geometria] {nombre_cond}: INF-METHOD=CRACK -> "
                          f"AIR-CHANGES/HR={c['infiltration']} es una referencia "
                          f"(presión de ensayo), no se aplica literal. "
                          f"infiltracion={inf_r} ren/h [{origen_r}] + "
                          f"ventilacion={vent_r} ren/h{_rec} = {infil} ren/h.")
            else:
                inf_r, _vent_r, _origen_r = _resolver_inf_vent(nombre_cond, _ac_ref)
                infil = inf_r
            comp_st = {
                "type": "Space_type",
                "name": st_name,
                "people_sensible": c["people_sensible"],
                "people_latent": c["people_latent"],
                "people_radiant_fraction": c["people_radiant_fraction"],
                "other_gains_radiant_fraction": c["other_gains_radiant_fraction"],
                "light_radiant_fraction": c["light_radiant_fraction"],
                "other_gains_latent_fraction": c["other_gains_latent_fraction"],
            }
            # Horarios REALES de HULC, uno por carga (ocupación, iluminación,
            # equipos e infiltración pueden tener perfiles distintos).
            h_ocu = horarios_map.get(c.get("people_schedule", "")) if horarios_map else None
            h_ilu = horarios_map.get(c.get("lighting_schedule", "")) if horarios_map else None
            h_equ = horarios_map.get(c.get("equip_schedule", "")) if horarios_map else None
            h_inf = horarios_map.get(c.get("inf_schedule", "")) if horarios_map else None

            if h_ocu or h_ilu or h_equ or h_inf:
                # Cada carga se modula con SU perfil; las que no tengan horario
                # quedan constantes.
                variables, usadas = [], {}
                for etiqueta, hname in (("o", h_ocu), ("l", h_ilu),
                                        ("e", h_equ), ("i", h_inf)):
                    if hname:
                        if hname not in usadas:
                            usadas[hname] = etiqueta
                            variables.append(f"{etiqueta} = {hname}.values")
                        else:
                            # Dos cargas comparten perfil: reutilizar variable.
                            usadas[hname] = usadas[hname]
                f_ocu = usadas.get(h_ocu, "") if h_ocu else ""
                f_ilu = usadas.get(h_ilu, "") if h_ilu else ""
                f_equ = usadas.get(h_equ, "") if h_equ else ""
                f_inf = usadas.get(h_inf, "") if h_inf else ""
                comp_st["input_variables"] = variables
                comp_st["people_density"] = (
                    f"{c['people_density']}*{f_ocu}" if f_ocu else str(c["people_density"]))
                comp_st["light_density"] = (
                    f"{c['light_density']}*{f_ilu}" if f_ilu else str(c["light_density"]))
                comp_st["other_gains_density"] = (
                    f"{c['other_gains_density']}*{f_equ}" if f_equ else str(c["other_gains_density"]))
                comp_st["infiltration"] = (
                    f"{infil}*{f_inf}" if f_inf else str(infil))
            elif usar_horarios_cte:
                # Sin horarios de HULC: perfil genérico del CTE.
                comp_st["input_variables"] = ["f = anual_cargas.values"]
                comp_st["people_density"] = f"{c['people_density']}*f"
                comp_st["light_density"] = f"{c['light_density']}*f"
                comp_st["other_gains_density"] = f"{c['other_gains_density']}*f"
                # infil ya incluye la ventilación resuelta (para CRACK).
                comp_st["infiltration"] = str(infil)
            else:
                comp_st["people_density"] = str(c["people_density"])
                comp_st["light_density"] = str(c["light_density"])
                comp_st["other_gains_density"] = str(c["other_gains_density"])
                comp_st["infiltration"] = str(infil)
            componentes.append(comp_st)
            space_types_generados[nombre_cond] = st_name

    if not space_types_generados:
        # Respaldo: un único Space_type genérico para todo el edificio (solo si
        # el .ctehexml no trae ninguna SPACE-CONDITIONS).
        _inf_g, _vent_g, _origen_g = _resolver_inf_vent(None)
        _infil_g = round(_inf_g + _vent_g, 4)
        if usar_horarios_cte:
            componentes.append({
                "type": "Space_type",
                "name": nombre_space_type,
                "input_variables": ["f = anual_cargas.values"],
                "people_density": "0.03*f",
                "light_density": f"{mitad_carga}*f",
                "other_gains_density": f"{mitad_carga}*f",
                "infiltration": str(_infil_g),
            })
        else:
            componentes.append({
                "type": "Space_type",
                "name": nombre_space_type,
                "people_density": "0.03",
                "light_density": str(mitad_carga),
                "other_gains_density": str(mitad_carga),
                "infiltration": str(_infil_g),
            })

    # --- Material de terreno para superficies UNDERGROUND ---
    # Las superficies en contacto con el terreno necesitan un ground_material.
    # Usamos un material genérico de terreno (valores típicos de suelo).
    nombre_terreno = "Terreno_generico"
    componentes.append({
        "type": "Material",
        "name": nombre_terreno,
        "conductivity": 2.0,
        "density": 2050.0,
        "specific_heat": 1840.0,
    })

    aperturas = []  # se añaden al final, tras las superficies
    nombres_espacios = []  # lista de (nombre, tipo) para los sistemas HVAC

    for planta in plantas:
        z_planta = planta["z"]

        for esp in planta["espacios"]:
            poligono = esp["poligono"]

            # --- Space ---
            # floor_area y volume a partir del polígono y la altura.
            area = _area_poligono(poligono) if poligono else 1.0
            altura = esp["altura"]
            # Space_type: el que corresponde a las SPACE-CONDITIONS que declara
            # este espacio en el .ctehexml; si no se han extraído, el genérico.
            st_esp = space_types_generados.get(esp.get("space_conditions", ""),
                                               nombre_space_type)
            comp_space = {
                "type": "Space",
                "name": esp["nombre"],
                "building": nombre_edificio,
                # OJO: el parámetro se llama "spaces_type" (con S), tal como
                # aparece en el ejemplo de la documentación de OpenSimula.
                "spaces_type": st_esp,
                "floor_area": round(area, 4),
                "volume": round(area * altura, 4),
            }
            # furniture_weight real de HULC, si hay SPACE-CONDITIONS para este
            # espacio: FURN-WEIGHT (kg/m² de mobiliario) x FURN-FRACTION
            # (fracción del suelo cubierta) = kg/m² de suelo TOTAL, que es lo
            # que pide Space.furniture_weight. Sin este dato, se deja el valor
            # por defecto de OpenSimula (10 kg/m²).
            cond_esp = (space_conditions or {}).get(esp.get("space_conditions", ""))
            if cond_esp is not None:
                peso_mob = cond_esp.get("furn_weight", 0.0) * cond_esp.get("furn_fraction", 0.0)
                if peso_mob > 0:
                    comp_space["furniture_weight"] = round(peso_mob, 4)
            componentes.append(comp_space)
            nombres_espacios.append((esp["nombre"], esp.get("tipo", "")))

            # Control del aplanado de cubierta: un tejado a varias aguas son
            # VARIAS superficies ROOF (una por faldón). Al aplanar, todas se
            # colapsan en UN ÚNICO techo plano; este flag evita generar un
            # techo duplicado por cada faldón (lo que apilaría 2,3,4... techos
            # de 64 m² sobre el mismo espacio e inflaría las pérdidas).
            cubierta_plana_emitida = False

            # Espesor REAL del muro perimetral enterrado de este espacio (para
            # exterior_perimeter_wall_thickness de su solera UNDERGROUND). Se
            # busca entre los propios muros UNDERGROUND-WALL del espacio,
            # sumando los espesores de la construcción que usan (dato real de
            # HULC, vía 'espesores_construcciones'). Si el espacio no tiene
            # muros enterrados propios o no hay datos, se cae al valor por
            # defecto de OpenSimula (0.3 m) más adelante.
            espesor_muro_terreno = None
            if espesores_construcciones:
                for s_probe in esp["superficies"]:
                    tipo_probe = _TIPO_SUPERFICIE.get(s_probe["tipo_hulc"], "EXTERIOR")
                    tilt_probe = s_probe.get("tilt", None)
                    es_horizontal_probe = (tilt_probe is not None
                                            and (tilt_probe < 30 or tilt_probe > 150))
                    if (tipo_probe == "UNDERGROUND" and not es_horizontal_probe
                            and s_probe.get("construccion")):
                        e = espesores_construcciones.get(s_probe["construccion"])
                        if e:
                            espesor_muro_terreno = e
                            break

            # --- Building_surface por cada muro ---
            for s in esp["superficies"]:
                surface_type = _TIPO_SUPERFICIE.get(s["tipo_hulc"], "EXTERIOR")

                # MUROS VERTICALES ENTERRADOS (p. ej. los muretes de la cámara
                # sanitaria). HULC los declara en el .ctehexml como objetos
                # UNDERGROUND-WALL (LOCATION = SPACE-Vn, construcción "MURO
                # CAMARA SANITARIA" / "MURO CON TERRENO"), es decir, en contacto
                # con el terreno.
                #
                # muros_verticales_underground = True (por defecto): se respeta
                # esa clasificación de HULC y van como UNDERGROUND (OpenSimula
                # les aplica su ISO 13370, pensada para soleras horizontales:
                # la física no es perfecta para un muro vertical, pero conserva
                # el contacto con el terreno). Es lo más fiel al .ctehexml y lo
                # que se validó como más parecido a HULC en el edificio ATECYR.
                #
                # = False: SOLO diagnóstico. Reclasifica esos muros a EXTERIOR
                # (les añade sol y aire exterior que HULC nunca les aplica);
                # aparta la ISO 13370 de OpenSimula sobre superficies verticales
                # a costa de apartarse de lo que dice HULC. Las soleras
                # horizontales van como UNDERGROUND en los dos casos.
                if surface_type == "UNDERGROUND" and not muros_verticales_underground:
                    tilt = s.get("tilt", None)
                    es_horizontal = (tilt is not None and (tilt < 30 or tilt > 150))
                    if not es_horizontal:
                        surface_type = "EXTERIOR"

                comp = {
                    "type": "Building_surface",
                    "name": s["nombre"],
                    "surface_type": surface_type,
                }
                # El parámetro "spaces" es SIEMPRE una lista (component-list),
                # también para EXTERIOR/UNDERGROUND: el ejemplo oficial de
                # Building_surface en la documentación de OpenSimula usa
                # "spaces": ["space_1"] con surface_type = "EXTERIOR". Para
                # INTERIOR/VIRTUAL la lista lleva dos elementos [lado0, lado1].
                if surface_type in ("INTERIOR", "VIRTUAL"):
                    if s.get("vecino"):
                        # Partición normal entre dos espacios del modelo.
                        comp["spaces"] = [esp["nombre"], s["vecino"]]
                    else:
                        # MEDIANERA: muro interior (INTERIOR-WALL de HULC) cuyo
                        # NEXT-TO está vacío porque al otro lado hay OTRO edificio
                        # (bloque contiguo), no un espacio de este modelo. HULC no
                        # le asigna espacio vecino. OpenSimula, en cambio, exige
                        # que una superficie INTERIOR tenga DOS espacios en su
                        # lista (Building_surface.py comprueba spaces.value[1]),
                        # por lo que una lista de un solo elemento provoca
                        # IndexError al hacer el check.
                        #
                        # Solución: tratarla como ADIABÁTICA emparejando el
                        # espacio consigo mismo -> spaces = [esp, esp]. Al estar
                        # los dos lados al mismo espacio (misma temperatura), no
                        # hay flujo neto de calor a través del muro, que es
                        # justo lo que representa una medianera contra otro
                        # edificio climatizado a temperatura similar.
                        comp["spaces"] = [esp["nombre"], esp["nombre"]]
                else:
                    comp["spaces"] = [esp["nombre"]]
                if s.get("construccion"):
                    comp["construction"] = s["construccion"]
                # Las superficies enterradas necesitan el material del terreno.
                # Además, OpenSimula MODIFICA la construcción de cada superficie
                # underground (le añade una capa de terreno). Si varias
                # superficies comparten la misma construcción, esa modificación
                # las descuadra. Por eso cada underground usa una COPIA propia
                # de su construcción, con nombre único. La copia real se crea en
                # la función principal (que tiene acceso a las construcciones).
                if surface_type == "UNDERGROUND":
                    comp["ground_material"] = nombre_terreno
                    if s.get("construccion"):
                        nombre_copia = f"{s['construccion']}__{s['nombre']}"
                        comp["construction"] = nombre_copia
                    # Parámetros del cálculo de soleras según ISO 13370.
                    # Los ponemos explícitos (aunque tengan valor por defecto)
                    # para asegurar que el cálculo de la construcción enterrada
                    # se inicializa correctamente.
                    comp["exterior_perimeter_fraction"] = 1.0
                    # REVERTIDO (ver más abajo): usar el espesor real del muro
                    # perimetral (0.205 m en vez de 0.3 m por defecto) dispara
                    # un ValueError dentro de OpenSimula (Construction._B_roots_/
                    # _H_Matrix_Layer_: math.sqrt(tau*s) recibe un valor
                    # negativo por precisión numérica, -6.74e-19) al construir
                    # la función de transferencia térmica de la construcción
                    # UNDERGROUND. Es un caso límite del propio OpenSimula, no
                    # de estos datos en sí (0.205 es un valor de entrada
                    # perfectamente normal). Mientras no se investigue más a
                    # fondo (o se corrija en OpenSimula), nos quedamos con el
                    # valor por defecto de OpenSimula (0.3 m), que sí funciona.
                    comp["exterior_perimeter_wall_thickness"] = 0.3
                    comp["groundwater_depth"] = 0.0

                # --- Aplanado de cubierta (SOLO diagnóstico, falsea la
                # geometría; ver docstring) ---
                # Con aplanar_cubierta=True, todos los ROOF explícitos del
                # espacio (planos o inclinados) se consolidan en un único techo
                # horizontal a la cota del alero, con la forma real del polígono
                # del espacio. Se incluyen también los ROOF ya planos en origen:
                # si se dejaran con su geometría explícita quedarían solapados
                # con el techo aplanado (dos capas de tejado sobre la misma
                # zona), lo que descuadra el cierre radiante del espacio y
                # dispara errores de Shapely en el cálculo de sombras.
                es_cubierta_inclinada = (
                    s["tipo_hulc"] == "ROOF"
                    and s["localizacion"] == "explicita"
                )
                if aplanar_cubierta and es_cubierta_inclinada and poligono:
                    # Si ya generamos el techo plano de este espacio (primer
                    # faldón), los demás faldones del mismo tejado se DESCARTAN:
                    # un único plano horizontal sustituye a todas las aguas.
                    if cubierta_plana_emitida:
                        continue
                    poligono_limpio = _quitar_vertices_colineales(poligono)
                    xs = [v[0] for v in poligono]
                    ys = [v[1] for v in poligono]
                    xmin, xmax = min(xs), max(xs)
                    ymin, ymax = min(ys), max(ys)
                    # Cota del techo plano: la del alero (z local + z planta).
                    # Es la base de los faldones; aplana la cumbrera hasta ahí.
                    z_techo = round(s["z"] + z_planta, 4)
                    comp["azimuth"] = 0.0
                    # TECHO horizontal: su NORMAL EXTERIOR mira hacia ARRIBA, así
                    # que altitude = +90 (convención de OpenSimula, verificada con
                    # el caso ASHRAE 200: roof_wall -> altitude=90).
                    comp["altitude"] = 90.0
                    # Se usa el polígono real: RECTANGLE solo si el espacio ya
                    # es rectangular, si no POLYGON con su forma. Con el
                    # rectángulo envolvente, un espacio en L (P03_E01) daría un
                    # tejado ~20-25% mayor que el suelo real.
                    es_rectangulo = len(poligono_limpio) == 4
                    if es_rectangulo:
                        es_rectangulo = all(
                            (abs(v[0] - xmin) < 1e-6 or abs(v[0] - xmax) < 1e-6)
                            and (abs(v[1] - ymin) < 1e-6 or abs(v[1] - ymax) < 1e-6)
                            for v in poligono_limpio)
                    if es_rectangulo:
                        comp["shape"] = "RECTANGLE"
                        comp["ref_point"] = [round(xmin, 4), round(ymin, 4), z_techo]
                        comp["width"] = round(xmax - xmin, 4)
                        comp["height"] = round(ymax - ymin, 4)
                    else:
                        comp["shape"] = "POLYGON"
                        # Mismo convenio que el caso TECHO general: origen en
                        # (xmin, ymin), sin invertir eje Y (normal hacia
                        # arriba, mismo sentido de giro que trae "poligono").
                        # Se usa poligono_limpio (sin vértices colineales
                        # redundantes) por el mismo motivo que en el caso
                        # general: evitar errores de Shapely en el cálculo de
                        # sombras.
                        comp["ref_point"] = [round(xmin, 4), round(ymin, 4), z_techo]
                        comp["x_polygon"] = [round(v[0] - xmin, 4) for v in poligono_limpio]
                        comp["y_polygon"] = [round(v[1] - ymin, 4) for v in poligono_limpio]
                    componentes.append(comp)
                    cubierta_plana_emitida = True
                    # Una cubierta no tiene huecos; saltamos al siguiente muro.
                    continue

                if s["localizacion"] == "explicita":
                    # Superficies EXPLÍCITAS (cubiertas inclinadas, muros y
                    # forjados que HULC define con su propio polígono local +
                    # X,Y,Z + AZIMUTH + TILT).
                    #
                    # CORRECCIÓN CLAVE de la geometría: NO se puede usar el
                    # polígono local de HULC directamente como polígono de
                    # OpenSimula (convenciones de coordenadas de superficie
                    # distintas -> faldones y forjados "volando" fuera del
                    # edificio). En su lugar:
                    #   1) reconstruimos los vértices 3D de MUNDO con la
                    #      convención de HULC (Z local + cota de planta), y
                    #   2) los re-expresamos como superficie POLYGON de
                    #      OpenSimula (azimuth, altitude, ref_point, x/y_polygon).
                    # Round-trip verificado con ~1e-2 m en muros y cubiertas.
                    poly_local = s.get("poligono_local", [])
                    z_mundo = s["z"] + z_planta
                    if poly_local:
                        az_os, alt_os, ref_pt, x_poly, y_poly = \
                            superficie_explicita_a_opensimula(
                                s["x"], s["y"], z_mundo,
                                s["azimuth"], s["tilt"], poly_local)
                        comp["shape"] = "POLYGON"
                        comp["ref_point"] = ref_pt
                        comp["azimuth"] = az_os
                        comp["altitude"] = alt_os
                        comp["x_polygon"] = x_poly
                        comp["y_polygon"] = y_poly
                    else:
                        # Sin polígono local: caemos a RECTANGLE con la
                        # conversión directa de ángulos (caso poco frecuente).
                        comp["shape"] = "RECTANGLE"
                        comp["ref_point"] = [round(s["x"], 4),
                                             round(s["y"], 4),
                                             round(z_mundo, 4)]
                        comp["azimuth"] = _azimut_a_opensimula(s["azimuth"])
                        comp["altitude"] = _tilt_a_altitude(s["tilt"])
                elif s["localizacion"] == "implicita" and "lado" in s:
                    p1, p2 = s["lado"]
                    comp["shape"] = "RECTANGLE"
                    # ref_point = primer vértice del lado (p1), a la cota Z del
                    # suelo del espacio. Esto se ha CONFIRMADO comparando con
                    # los muros explícitos de la planta bajo-cubierta (P03),
                    # donde HULC da el X,Y directamente: en todos los casos el
                    # ref_point coincide con el PRIMER vértice del lado del
                    # polígono (p1), no con el segundo. Desde p1, el eje X de la
                    # superficie (ancho) recorre el lado hacia p2.
                    comp["ref_point"] = [round(p1[0], 4), round(p1[1], 4),
                                         round(z_planta, 4)]
                    comp["width"] = s["ancho_calc"]
                    comp["height"] = round(altura, 4)
                    # azimuth_calc ya está en el rango -180/180 de OpenSimula
                    # (lo devuelve azimut_de_lado), no hay que reconvertirlo.
                    comp["azimuth"] = round(s["azimuth_calc"], 2)
                    comp["altitude"] = 0.0  # muro vertical
                else:
                    # Superficies horizontales (suelos y techos: BOTTOM/TOP).
                    #
                    # CONVENCIÓN DE OpenSimula: el parámetro "altitude" se refiere
                    # a la NORMAL EXTERIOR de la superficie (Surface.py línea 15-16:
                    # azimuth = "...horizontal projection of exterior normal";
                    # altitude = "facing up: 90º, facing down: -90º").
                    #   - SUELO (BOTTOM): normal exterior hacia ABAJO -> -90.
                    #   - TECHO (TOP):    normal exterior hacia ARRIBA -> +90.
                    #
                    # Verificado con el caso ASHRAE 200 (BESTEST, validado contra
                    # otros programas): floor_wall -> altitude=-90, roof_wall -> +90.
                    #
                    # Por qué NO es "la cara interior": Space._create_surfaces_list
                    # asigna side=1 a todas las superficies EXTERIOR/UNDERGROUND de
                    # un espacio, y Surface.orientation_angle("altitude", side=1)
                    # devuelve -altitude. Space._create_dist_vectors detecta como
                    # SUELO las superficies cuyo orientation_angle vale +90; para un
                    # suelo con altitude=-90 eso da -(-90) = +90 -> se detecta bien.
                    # Con el criterio invertido (suelo=+90) daba -90, floor_area
                    # quedaba en 0 m² y la radiación solar directa se repartía sobre
                    # total_area en vez de concentrarse en el suelo, disparando la
                    # demanda.
                    if poligono:
                        poligono_limpio = _quitar_vertices_colineales(poligono)
                        xs = [v[0] for v in poligono]
                        ys = [v[1] for v in poligono]
                        xmin, xmax = min(xs), max(xs)
                        ymin, ymax = min(ys), max(ys)
                        loc = s.get("location", "")
                        es_suelo = (loc == "BOTTOM")
                        # z de la superficie: suelo a la cota de la planta;
                        # techo a la cota de la planta + altura del espacio.
                        z_sup = z_planta if es_suelo else z_planta + altura
                        comp["azimuth"] = 0.0
                        if es_suelo:
                            comp["altitude"] = -90.0   # normal exterior hacia abajo
                            y_ref = ymax
                        else:
                            comp["altitude"] = 90.0    # normal exterior hacia arriba
                            y_ref = ymin
                        comp["ref_point"] = [round(xmin, 4), round(y_ref, 4),
                                             round(z_sup, 4)]
                        # Suelo/techo con la forma real del espacio: RECTANGLE
                        # solo si el polígono ya es un rectángulo, si no POLYGON.
                        # Con el rectángulo envolvente, un espacio no rectangular
                        # (edificio con un entrante) genera un suelo/techo que
                        # sobresale de los muros y "flota" en show_3D().
                        es_rectangulo = len(poligono_limpio) == 4
                        if es_rectangulo:
                            # Con 4 vértices, comprobar que de verdad es un
                            # rectángulo (todas las x están en {xmin,xmax} y
                            # todas las y en {ymin,ymax}).
                            es_rectangulo = all(
                                (abs(v[0] - xmin) < 1e-6 or abs(v[0] - xmax) < 1e-6)
                                and (abs(v[1] - ymin) < 1e-6 or abs(v[1] - ymax) < 1e-6)
                                for v in poligono_limpio)
                        if es_rectangulo:
                            comp["shape"] = "RECTANGLE"
                            comp["width"] = round(xmax - xmin, 4)
                            comp["height"] = round(ymax - ymin, 4)
                        else:
                            comp["shape"] = "POLYGON"
                            # Mismo convenio que el RECTANGLE de arriba: origen
                            # en (xmin, y_ref); suelo con eje Y invertido
                            # (y_ref=ymax, crece hacia -Y), techo sin invertir
                            # (y_ref=ymin, crece hacia +Y).
                            #
                            # OJO CON EL SENTIDO DE GIRO: el polígono original
                            # ("poligono", coordenadas de mundo) tiene un
                            # sentido de giro nativo (horario/CW en este
                            # proyecto). El caso TECHO solo traslada
                            # (y_polygon = v[1]-ymin), así que conserva ese
                            # mismo sentido -y funciona correctamente,
                            # verificado con ASHRAE 140-. El caso SUELO invierte
                            # el eje Y (y_polygon = ymax-v[1]), y una reflexión
                            # SIEMPRE invierte el sentido de giro de un
                            # polígono (CW -> CCW). Sin corregirlo, el suelo
                            # queda con un sentido de giro distinto al del
                            # techo para la misma geometría de espacio, lo que
                            # descuadra la normal/orientación de la superficie
                            # en OpenSimula. Se corrige invirtiendo también el
                            # ORDEN de los vértices en el caso suelo, para que
                            # las dos reflexiones (eje Y + orden) se cancelen y
                            # el sentido final vuelva a coincidir con el del
                            # techo.
                            #
                            # Se usa poligono_limpio (sin vértices colineales
                            # redundantes) en vez de poligono: los puntos
                            # colineales (varias esquinas de muros distintos
                            # a lo largo del mismo borde recto) no cambian la
                            # forma, pero pueden hacer que Shapely (usado por
                            # OpenSimula para el cálculo de sombras) falle con
                            # errores de "non-noded intersection".
                            if es_suelo:
                                poligono_ordenado = list(reversed(poligono_limpio))
                                comp["x_polygon"] = [round(v[0] - xmin, 4) for v in poligono_ordenado]
                                comp["y_polygon"] = [round(ymax - v[1], 4) for v in poligono_ordenado]
                            else:
                                comp["x_polygon"] = [round(v[0] - xmin, 4) for v in poligono_limpio]
                                comp["y_polygon"] = [round(v[1] - ymin, 4) for v in poligono_limpio]
                    else:
                        comp["shape"] = "RECTANGLE"
                        loc = s.get("location", "")
                        # Normal exterior: suelo (BOTTOM) -> -90; techo (TOP) -> +90.
                        comp["altitude"] = -90.0 if loc == "BOTTOM" else 90.0

                # --- Orden de "spaces" en forjados INTERIOR horizontales ---
                # OpenSimula asigna el "side" de cada espacio por su POSICIÓN en la
                # lista "spaces": spaces[0] -> side 0 (la cara hacia la que apunta la
                # normal exterior), spaces[1] -> side 1 (la cara opuesta).
                # Surface.orientation_angle("altitude", side) devuelve +altitude para
                # side=0 y -altitude para side=1, y Space._create_dist_vectors
                # considera SUELO de un espacio la superficie cuyo orientation_angle
                # visto por ese espacio vale +90.
                #
                # De ahí la regla, para un forjado horizontal entre dos plantas:
                #   altitude = -90 (cara 0 hacia ABAJO)  -> spaces = [abajo, arriba]
                #   altitude = +90 (cara 0 hacia ARRIBA) -> spaces = [arriba, abajo]
                # Así el espacio para el que el forjado es SUELO siempre acaba viendo
                # +90 y su floor_area se detecta correctamente.
                #
                # El conversor construye "spaces" como [propietario, vecino] sin
                # mirar la orientación, por lo que aquí se reordena. Quién está
                # arriba y quién abajo se deduce de la GEOMETRÍA: el espacio cuyo
                # suelo está a la cota del forjado es el de arriba. Esa cota se
                # calcula en la pasada posterior (ver _corregir_orden_spaces_
                # forjados), porque aquí todavía no se conocen las cotas de todos
                # los espacios.
                #
                # Sin esta corrección, el suelo de los espacios superiores no se
                # detecta (floor_area = 0 o incompleta) y la radiación solar directa
                # se reparte sobre toda la envolvente en vez de concentrarse en el
                # suelo, lo que desvirtúa el balance térmico.

                componentes.append(comp)

                # --- Opening por cada hueco del muro ---
                for h in s["huecos"]:
                    aperturas.append({
                        "type": "Opening",
                        "name": h["nombre"],
                        "surface": s["nombre"],
                        "opening_type": h["gap"],
                        "shape": "RECTANGLE",
                        "width": h["ancho"],
                        "height": h["alto"],
                        "ref_point": [round(h["x"], 4), round(h["y"], 4)],
                        "setback": h.get("setback", 0.0),
                    })

    # Las aperturas (Opening) van al final: referencian Building_surface.
    componentes.extend(aperturas)

    # --- Corrección del orden de "spaces" en los forjados INTERIOR horizontales ---
    # Se hace en una pasada posterior porque necesita las cotas de TODOS los
    # espacios, que solo se conocen una vez generadas todas las superficies.
    _corregir_orden_spaces_forjados(componentes)


    # Sistemas de climatización (opcional). IMPORTANTE: solo se climatizan los
    # espacios ACONDICIONADOS (TYPE=CONDITIONED en HULC). Los espacios no
    # habitables (UNHABITED), como la cámara sanitaria, quedan en oscilación
    # libre (sin sistema), igual que en HULC. Climatizarlos falsearía las
    # cargas, porque obligaría a calentar/enfriar grandes volúmenes no
    # habitables con mucha superficie expuesta.
    if incluir_hvac:
        for nombre_esp, tipo_esp in nombres_espacios:
            # Qué espacios llevan HVAC_perfect_system (y por tanto aportan
            # demanda). El tipo viene del campo TYPE del objeto SPACE de HULC:
            #   - CONDITIONED   : espacio acondicionado, con equipo -> lleva
            #                     sistema, aporta demanda.
            #   - UNCONDITIONED : habitable sin equipo -> NO lleva sistema, flota
            #                     (en HULC su demanda es 0). Se comprobó con
            #                     P02_E05.txt del edificio ATECYR: 0 h de
            #                     funcionamiento de equipo, carga total 0.
            #   - UNHABITED     : no habitable (cámara sanitaria, bajocubierta,
            #                     P02_E06...) -> NO lleva sistema, flota.
            # Con incluir_unconditioned=True (solo para diagnóstico) los
            # UNCONDITIONED también reciben sistema.
            tipos_con_sistema = ("CONDITIONED",)
            if incluir_unconditioned:
                tipos_con_sistema = ("CONDITIONED", "UNCONDITIONED")
            if tipo_esp not in tipos_con_sistema:
                continue  # UNCONDITIONED / UNHABITED / otros: sin sistema

            # Condiciones de sistema REALES de HULC para este espacio, si se
            # han extraído del .ctehexml.
            sc_nombre = (system_conditions_por_espacio or {}).get(nombre_esp, "")
            sc = (system_conditions or {}).get(sc_nombre)

            if sc and horarios_map:
                # HULC define, por espacio:
                #   HEATING/COOLING-SCHEDULE -> cuándo funciona el sistema
                #   HEAT-TEMP-SCH / COOL-TEMP-SCH -> consignas
                #   SEASON-SCH -> temporada: 1 = calefacción, 0 = refrigeración
                #
                # OpenSimula solo tiene un "system_on_off" común, así que la
                # temporada se aplica a las CONSIGNAS: en verano (season=0) la
                # consigna de calefacción se hace inalcanzable (-100 °C) para
                # que no caliente, y en invierno (season=1) la de refrigeración
                # se sube a 100 °C para que no enfríe. Así se reproduce el
                # comportamiento estacional de HULC.
                #
                # Sin esto, el sistema mantiene 20 °C también en verano y el
                # espacio nunca alcanza los 25 °C de la consigna de frío: la
                # demanda de refrigeración sale prácticamente nula.
                variables, expr = [], {}
                h_fun = horarios_map.get(sc.get("heating_schedule", ""))
                h_sea = horarios_map.get(sc.get("season_sch", ""))
                h_tc = horarios_map.get(sc.get("heat_temp_sch", ""))
                h_tr = horarios_map.get(sc.get("cool_temp_sch", ""))

                if h_fun:
                    variables.append(f"fun = {h_fun}.values")
                    expr["on_off"] = "fun"
                else:
                    expr["on_off"] = "1"

                if h_tc:
                    variables.append(f"tc = {h_tc}.values")
                    base_tc = "tc"
                else:
                    base_tc = str(heating_setpoint)
                if h_tr:
                    variables.append(f"tr = {h_tr}.values")
                    base_tr = "tr"
                else:
                    base_tr = str(cooling_setpoint)

                if h_sea:
                    variables.append(f"sea = {h_sea}.values")
                    # season=1 (invierno): calefacción a su consigna, frío a 100
                    # season=0 (verano):   calefacción a -100, frío a su consigna
                    heat_sp = f"sea*({base_tc}) + (1-sea)*(-100)"
                    cool_sp = f"sea*100 + (1-sea)*({base_tr})"
                else:
                    heat_sp, cool_sp = base_tc, base_tr

                componentes.append({
                    "type": "HVAC_perfect_system",
                    "name": f"HVAC_{nombre_esp}",
                    "spaces": nombre_esp,
                    "input_variables": variables,
                    "outdoor_air_flow": str(sc.get("outside_air_flow", 0.0)),
                    "heating_setpoint": heat_sp,
                    "cooling_setpoint": cool_sp,
                    "system_on_off": expr["on_off"],
                })
            elif usar_horarios_cte:
                # Sin condiciones de HULC: consignas con el perfil genérico CTE.
                componentes.append({
                    "type": "HVAC_perfect_system",
                    "name": f"HVAC_{nombre_esp}",
                    "spaces": nombre_esp,
                    "input_variables": ["tc = anual_calef.values",
                                        "tr = anual_refrig.values"],
                    "outdoor_air_flow": "0",
                    "heating_setpoint": "tc",
                    "cooling_setpoint": "tr",
                    "system_on_off": "1",
                })
            else:
                componentes.append({
                    "type": "HVAC_perfect_system",
                    "name": f"HVAC_{nombre_esp}",
                    "spaces": nombre_esp,
                    "outdoor_air_flow": "0",
                    "heating_setpoint": str(heating_setpoint),
                    "cooling_setpoint": str(cooling_setpoint),
                    "system_on_off": "1",
                })

    # Si se usan horarios CTE, añadimos los componentes de horario al principio
    # de la lista (deben existir antes de que los referencien Space_type y HVAC).
    if usar_horarios_cte:
        componentes = _componentes_horario_cte() + componentes

    return componentes


def _area_poligono(poly):
    """Área (positiva) de un polígono por la fórmula del zapatero."""
    s = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def _quitar_vertices_colineales(poly, tol=1e-6):
    """
    Quita de un polígono cerrado los vértices redundantes que caen sobre la
    misma línea recta que sus dos vecinos (p.ej. varios puntos seguidos a lo
    largo de un mismo borde recto, que aparecen cuando el polígono del
    espacio se arma a partir de las esquinas de muchos muros distintos a lo
    largo de la misma fachada). No cambian la forma real del polígono, pero
    esos puntos colineales pueden hacer que motores geométricos como Shapely
    (usado por OpenSimula para el cálculo de sombras) fallen con errores de
    tipo "non-noded intersection" al operar con polígonos casi-coincidentes.
    """
    n = len(poly)
    if n < 4:
        return list(poly)
    resultado = []
    for i in range(n):
        p_prev = poly[(i - 1) % n]
        p_cur = poly[i]
        p_next = poly[(i + 1) % n]
        # Área con signo del triángulo (p_prev, p_cur, p_next). Si es ~0, los
        # tres puntos están alineados y p_cur es redundante.
        area2 = ((p_cur[0] - p_prev[0]) * (p_next[1] - p_prev[1])
                 - (p_next[0] - p_prev[0]) * (p_cur[1] - p_prev[1]))
        if abs(area2) > tol:
            resultado.append(p_cur)
    return resultado if len(resultado) >= 3 else list(poly)


# ===========================================================================
# 5. DEMO / INSPECCIÓN
# ===========================================================================

if __name__ == "__main__":
    import sys

    # Reutilizamos la extracción del bloque BDL del módulo principal.
    from hulc_to_opensimula import leer_ctehexml, extraer_bloque_bdl

    if len(sys.argv) < 2:
        print("Uso: python hulc_geometria.py archivo.ctehexml")
        sys.exit(1)

    texto = leer_ctehexml(sys.argv[1])
    bdl = extraer_bloque_bdl(texto)
    arbol = parsear_arbol_bdl(bdl)
    plantas = extraer_geometria(arbol)

    print("=" * 70)
    print("GEOMETRÍA EXTRAÍDA")
    print("=" * 70)
    for planta in plantas:
        print(f"\nPLANTA {planta['nombre']}  (Z={planta['z']}, "
              f"altura={planta['altura']})")
        for esp in planta["espacios"]:
            print(f"  ESPACIO {esp['nombre']}  tipo={esp['tipo']}  "
                  f"altura={esp['altura']}")
            print(f"    polígono: {esp['poligono']}")
            for s in esp["superficies"]:
                if s["localizacion"] == "explicita":
                    print(f"    - {s['nombre']} [{s['tipo_hulc']}] EXPLÍCITA "
                          f"azimuth={s['azimuth']} tilt={s['tilt']} "
                          f"constr='{s['construccion']}' huecos={len(s['huecos'])}")
                else:
                    az = s.get("azimuth_calc", "?")
                    an = s.get("ancho_calc", "?")
                    print(f"    - {s['nombre']} [{s['tipo_hulc']}] IMPLÍCITA "
                          f"loc={s.get('location','?')} azimut_calc={az} "
                          f"ancho_calc={an} huecos={len(s['huecos'])}")

    # Generamos los componentes de OpenSimula y mostramos un resumen.
    componentes = geometria_a_componentes(plantas)
    from collections import Counter
    cuenta = Counter(c["type"] for c in componentes)
    print("\n" + "=" * 70)
    print("COMPONENTES OPENSIMULA GENERADOS (geometría)")
    print("=" * 70)
    for tipo, n in cuenta.items():
        print(f"  {tipo}: {n}")

    # Mostramos un ejemplo de cada tipo de superficie.
    print("\nEjemplo de Building_surface implícita (muro calculado):")
    for c in componentes:
        if c["type"] == "Building_surface" and "width" in c:
            import pprint
            pprint.pprint(c, sort_dicts=False)
            break
    print("\nEjemplo de Building_surface explícita:")
    for c in componentes:
        if c["type"] == "Building_surface" and "width" not in c and c.get("altitude") != -90.0 and "x_polygon" not in c:
            import pprint
            pprint.pprint(c, sort_dicts=False)
            break
