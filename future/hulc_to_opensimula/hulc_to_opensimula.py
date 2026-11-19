"""
hulc_to_opensimula.py
======================

Lectura de un archivo de entrada de HULC (.ctehexml) y conversión de sus datos
a un diccionario de Python con el formato que utiliza OpenSimula como entrada
(el que se pasa a la función `Project.read_dict()`).

------------------------------------------------------------------------------
CONTEXTO (importante para entender el código)
------------------------------------------------------------------------------
Un archivo .ctehexml de HULC NO es un XML homogéneo. Tiene dos partes:

  1. Una cabecera que sí es XML normal: <DatosGenerales>...</DatosGenerales>
     con datos administrativos y climáticos (zona climática, provincia, etc.).

  2. Una sección <EntradaGraficaLIDER> cuyo contenido va dentro de un bloque
     CDATA y NO es XML, sino el formato propio de LIDER/DOE-2 conocido como
     BDL (Building Description Language). Ahí está toda la información
     constructiva y geométrica del edificio.

El formato BDL se compone de "objetos" con esta forma:

        "NOMBRE_DEL_OBJETO" = TIPO_DE_OBJETO
            CLAVE1   = valor1
            CLAVE2   = ( valor_a, valor_b, valor_c )
            ...
            ..

  - La primera línea da el nombre (entre comillas) y el tipo del objeto.
  - Las líneas siguientes son pares CLAVE = VALOR.
  - Los valores pueden ser simples o listas entre paréntesis.
  - Cada objeto termina con una línea que contiene únicamente ".." .

En esta Fase 1 nos centramos en los objetos:
  - MATERIAL  -> componente "Material" de OpenSimula
  - LAYERS    -> componente "Construction" de OpenSimula

(En fases posteriores se añadirán huecos, espacios y geometría.)

------------------------------------------------------------------------------
LIMITACIÓN CONOCIDA (documentar en la memoria del TFG)
------------------------------------------------------------------------------
Las construcciones (LAYERS) referencian materiales por su nombre. Algunos de
esos materiales están definidos en el propio .ctehexml como objetos MATERIAL,
pero MUCHOS proceden de la base de datos de materiales de HULC (el archivo
BDRefASIT.mdb) y NO aparecen en el .ctehexml. El parser detecta y avisa de los
materiales que se referencian pero no están definidos. Resolver esas
referencias (leyendo la base de datos de HULC) queda fuera de la Fase 1.

Autor: [tu nombre] - TFG GITI, Universidad de Sevilla
"""

import re
import math
import xml.etree.ElementTree as ET


# ===========================================================================
# 1. LECTURA DEL ARCHIVO Y SEPARACIÓN DE LAS DOS PARTES
# ===========================================================================

def leer_ctehexml(ruta):
    """
    Lee el archivo .ctehexml completo y devuelve su contenido como texto.

    HULC guarda el archivo en UTF-8 con finales de línea de Windows (\\r\\n).
    Usamos utf-8 y dejamos que Python normalice los saltos de línea.
    """
    with open(ruta, "r", encoding="utf-8") as f:
        return f.read()


def extraer_bloque_bdl(texto_xml):
    """
    Extrae el texto BDL que está dentro de <EntradaGraficaLIDER> ... CDATA ...

    Devuelve únicamente el texto en formato BDL (sin las etiquetas XML ni el
    envoltorio CDATA), que es lo que luego parsearemos objeto a objeto.
    """
    # Buscamos el contenido entre las etiquetas de apertura y cierre.
    # re.DOTALL hace que "." también capture saltos de línea.
    patron = re.compile(
        r"<EntradaGraficaLIDER>\s*<!\[CDATA\[(.*?)\]\]>\s*</EntradaGraficaLIDER>",
        re.DOTALL,
    )
    coincidencia = patron.search(texto_xml)
    if coincidencia is None:
        raise ValueError(
            "No se ha encontrado la sección <EntradaGraficaLIDER> con CDATA. "
            "¿Es realmente un archivo .ctehexml de HULC?"
        )
    return coincidencia.group(1)


def extraer_datos_generales(texto_xml):
    """
    Parsea la parte XML de la cabecera (<DatosGenerales>) y devuelve un
    diccionario sencillo {etiqueta: texto} con los datos administrativos y
    climáticos. Lo usamos para rellenar el nombre del proyecto, etc.

    Nota: parseamos solo el fragmento <DatosGenerales> para evitar que el
    bloque BDL (que no es XML válido) rompa el parser de ElementTree.
    """
    patron = re.compile(r"<DatosGenerales>.*?</DatosGenerales>", re.DOTALL)
    coincidencia = patron.search(texto_xml)
    if coincidencia is None:
        return {}

    raiz = ET.fromstring(coincidencia.group(0))
    datos = {}
    for hijo in raiz:
        # Guardamos el texto de cada etiqueta (puede ser None si está vacía).
        datos[hijo.tag] = (hijo.text or "").strip()
    return datos


# ===========================================================================
# 2. PARSEO GENÉRICO DEL FORMATO BDL
# ===========================================================================

# Expresión regular para la cabecera de un objeto BDL:  "Nombre" = TIPO
# - Grupo 1: el nombre (lo que va entre comillas).
# - Grupo 2: el tipo (palabra en mayúsculas, admite guiones).
_RE_CABECERA_OBJETO = re.compile(r'^\s*"([^"]+)"\s*=\s*([A-Z][A-Z0-9\-]*)\s*$')

# Expresión regular para una línea  CLAVE = VALOR
_RE_PAR_CLAVE_VALOR = re.compile(r'^\s*([A-Za-z0-9_\-]+)\s*=\s*(.*?)\s*$')

# Nombre de la construcción que se asigna a la parte OPACA de los huecos
# (Opening_type). OpenSimula siempre necesita una "construction" para el hueco
# aunque su fracción opaca sea ~0 (por el residuo de coma flotante en
# 1 - glazing_fraction - frame_fraction). En puertas ciegas
# (frame_fraction = 1) esta construcción representa la hoja opaca de la puerta.
_CONSTRUCCION_HUECO_OPACO = "CONSTRUCCION_HUECO_OPACO"


def _parsear_valor(valor_texto):
    """
    Convierte el texto de la parte derecha de "CLAVE = VALOR" en un valor
    Python adecuado:
      - Una lista entre paréntesis  ( a, b, c )  ->  lista de valores.
      - Un texto entre comillas  "algo"  ->  str sin comillas.
      - Un número  ->  float o int.
      - El resto  ->  str tal cual (YES, NO, PROPERTIES, ...).
    """
    valor_texto = valor_texto.strip()

    # Caso lista: empieza por "(" y termina por ")"
    if valor_texto.startswith("(") and valor_texto.endswith(")"):
        interior = valor_texto[1:-1]
        elementos = [e.strip() for e in interior.split(",")]
        # Parseamos recursivamente cada elemento de la lista.
        return [_parsear_valor(e) for e in elementos if e != ""]

    # Caso texto entre comillas
    if len(valor_texto) >= 2 and valor_texto.startswith('"') and valor_texto.endswith('"'):
        return valor_texto[1:-1]

    # Caso número (intentamos int y luego float)
    try:
        if re.fullmatch(r"[-+]?\d+", valor_texto):
            return int(valor_texto)
        return float(valor_texto)
    except ValueError:
        # No es número: lo devolvemos como texto (YES, NO, etc.)
        return valor_texto


def parsear_objetos_bdl(texto_bdl):
    """
    Recorre el texto BDL línea a línea y construye una lista de objetos.

    Cada objeto se devuelve como un diccionario:
        {
            "nombre": "MURO EXTERIOR",
            "tipo":   "LAYERS",
            "props":  { "MATERIAL": [...], "THICKNESS": [...], ... }
        }

    Importante sobre la estructura: en BDL los objetos pueden estar ANIDADOS
    (por ejemplo un WINDOW dentro de un EXTERIOR-WALL dentro de un SPACE). Para
    la Fase 1 solo necesitamos MATERIAL y LAYERS, que están definidos en el
    nivel superior, así que usamos un parser "plano": cada vez que encontramos
    una cabecera de objeto empezamos uno nuevo y lo cerramos al llegar a "..".
    Esto recoge todos los objetos, también los anidados, como entradas
    independientes de la lista, lo cual nos vale perfectamente porque luego
    filtramos por tipo.
    """
    objetos = []
    objeto_actual = None
    clave_pendiente = None  # para valores que se reparten en varias líneas

    for linea in texto_bdl.splitlines():
        # ¿Es el cierre de un objeto?
        if linea.strip() == "..":
            if objeto_actual is not None:
                objetos.append(objeto_actual)
                objeto_actual = None
                clave_pendiente = None
            continue

        # ¿Es la cabecera de un objeto nuevo?  "Nombre" = TIPO
        m_cab = _RE_CABECERA_OBJETO.match(linea)
        if m_cab:
            # Si había uno abierto sin cerrar (raro), lo guardamos igualmente.
            if objeto_actual is not None:
                objetos.append(objeto_actual)
            objeto_actual = {
                "nombre": m_cab.group(1),
                "tipo": m_cab.group(2),
                "props": {},
            }
            clave_pendiente = None
            continue

        # Si no hay objeto abierto, ignoramos la línea (cabecera del fichero,
        # comentarios "$ ...", líneas sueltas de DATOS GENERALES, etc.).
        if objeto_actual is None:
            continue

        # ¿Es un par CLAVE = VALOR dentro del objeto?
        m_par = _RE_PAR_CLAVE_VALOR.match(linea)
        if m_par:
            clave = m_par.group(1)
            valor = _parsear_valor(m_par.group(2))
            objeto_actual["props"][clave] = valor
            clave_pendiente = None

    # Por si el texto termina sin un ".." final.
    if objeto_actual is not None:
        objetos.append(objeto_actual)

    return objetos


# ===========================================================================
# 3. CONVERSIÓN DE OBJETOS BDL A COMPONENTES DE OPENSIMULA
# ===========================================================================

def material_bdl_a_componente(obj):
    """
    Convierte un objeto BDL de tipo MATERIAL en un componente "Material" de
    OpenSimula.

    Mapeo de parámetros (HULC -> OpenSimula):
        CONDUCTIVITY   -> conductivity   [W/(m·K)]
        DENSITY        -> density        [kg/m³]
        SPECIFIC-HEAT  -> specific_heat  [J/(kg·K)]

    Algunos materiales en HULC se definen por RESISTANCE (cámaras de aire,
    por ejemplo) en lugar de por conductividad. En ese caso OpenSimula admite
    use_resistance=True y thermal_resistance. Lo contemplamos.
    """
    props = obj["props"]

    componente = {
        "type": "Material",
        "name": obj["nombre"],
    }

    # En BDL, la clave TYPE indica cómo está definido el material:
    #   TYPE = PROPERTIES  -> por conductividad, densidad y calor específico.
    #   TYPE = RESISTANCE  -> por resistencia térmica (cámaras de aire, etc.).
    tipo_def = props.get("TYPE", "PROPERTIES")

    if tipo_def == "RESISTANCE" or "RESISTANCE" in props:
        # Material definido por resistencia térmica.
        # OpenSimula: use_resistance=True + thermal_resistance.
        componente["use_resistance"] = True
        componente["thermal_resistance"] = float(props.get("RESISTANCE", 1))
        # density y specific_heat son obligatorios en OpenSimula aunque se use
        # resistencia; si no vienen, dejamos los valores por defecto del modelo.
        if "DENSITY" in props:
            componente["density"] = float(props["DENSITY"])
        if "SPECIFIC-HEAT" in props:
            componente["specific_heat"] = float(props["SPECIFIC-HEAT"])
    else:
        # Caso normal: definido por conductividad.
        componente["conductivity"] = float(props.get("CONDUCTIVITY", 1))
        componente["density"] = float(props.get("DENSITY", 1000))
        componente["specific_heat"] = float(props.get("SPECIFIC-HEAT", 1000))

    return componente


def construccion_bdl_a_componente(obj, absortancia_real=None):
    """
    Convierte un objeto BDL de tipo LAYERS en un componente "Construction" de
    OpenSimula.

    Mapeo de parámetros (HULC -> OpenSimula):
        MATERIAL   (lista de nombres)  -> materials   (component-list)
        THICKNESS  (lista de espesores)-> thicknesses (float-list)

    OpenSimula ordena las capas de la superficie 1 a la 2. HULC las da del
    exterior al interior; aquí las pasamos en el mismo orden en que aparecen.
    (Si en la validación con tu tutor se ve que el criterio de OpenSimula es el
    inverso, basta con invertir ambas listas.)

    absortancia_real: si se pasa (float), se usa como solar_alpha real en vez
    del valor por defecto 0.6. Viene del campo ABSORPTANCE que HULC pone en
    cada EXTERIOR-WALL/ROOF/UNDERGROUND-WALL (no en este objeto LAYERS),
    extraído aparte en ctehexml_a_diccionario y pasado aquí, porque este
    LAYERS puede ser compartido por varios muros -en este proyecto siempre
    con el mismo ABSORPTANCE, pero no tiene por qué ser así en otro proyecto-.
    """
    props = obj["props"]

    # MATERIAL y THICKNESS pueden venir como lista o, si solo hay una capa,
    # como valor simple. Normalizamos a lista siempre.
    materiales = props.get("MATERIAL", [])
    espesores = props.get("THICKNESS", [])
    if not isinstance(materiales, list):
        materiales = [materiales]
    if not isinstance(espesores, list):
        espesores = [espesores]

    solar_alpha_valor = 0.6 if absortancia_real is None else float(absortancia_real)

    componente = {
        "type": "Construction",
        "name": obj["nombre"],
        "materials": [str(m) for m in materiales],
        "thicknesses": [float(t) for t in espesores],
        # Propiedades RADIANTES de las dos caras [cara_exterior, cara_interior].
        #   - solar_alpha: HULC SÍ da este dato -en el objeto EXTERIOR-WALL/
        #     ROOF/UNDERGROUND-WALL, campo ABSORPTANCE, no en este objeto
        #     LAYERS-, extraído en ctehexml_a_diccionario y pasado aquí como
        #     absortancia_real. Si no hay dato real disponible (LAYERS sin
        #     ningún muro que la referencie con ABSORPTANCE), se cae al 0.6
        #     por defecto del CTE. La cara interior no tiene un dato
        #     equivalente en HULC; se deja igual a la exterior.
        #   - lw_epsilon (emisividad de onda larga): 0.9, valor estándar para
        #     materiales de construcción no metálicos. HULC no da ningún campo
        #     de emisividad en todo el proyecto (comprobado, ninguna aparición
        #     de EMISS/EMISSIVITY en el .ctehexml) -sigue siendo una
        #     invención nuestra sin dato real que la respalde-.
        "solar_alpha": [solar_alpha_valor, solar_alpha_valor],
        "lw_epsilon": [0.9, 0.9],
    }
    return componente


# ===========================================================================
# 3 ter. CONVERSIÓN DE HUECOS (FASE 2): vidrios, marcos y tipos de hueco
# ===========================================================================
#
# En HULC, un hueco (objeto GAP) se compone de:
#   - un vidrio  (objeto GLASS-TYPE, referenciado por GLASS-TYPE)
#   - un marco   (objeto NAME-FRAME, referenciado por NAME-FRAME)
#   - un porcentaje de marco (parámetro PORCENTAGE)
#
# En OpenSimula esto se traduce a tres componentes:
#   GLASS-TYPE  -> Glazing
#   NAME-FRAME  -> Frame
#   GAP         -> Opening_type  (que referencia un Glazing y un Frame)
#
# AVISO IMPORTANTE (documentar en la memoria):
# HULC describe el vidrio de forma SIMPLIFICADA, con el coeficiente de sombra
# (SHADING-COEF) y la conductancia del vidrio (GLASS-CONDUCTANCE). OpenSimula,
# en cambio, pide un modelo más detallado (transmitancia solar solar_tau,
# reflectancias, factor solar g, U, y curvas angulares). No hay equivalencia
# exacta, así que se usa el modelo "Simple Glazing System" publicado por LBNL
# (Arasteh, Kohler y Griffith, 2009 - el mismo que usa EnergyPlus para este
# caso, WindowMaterial:SimpleGlazingSystem), que convierte SOLO U y SHGC en el
# resto de propiedades ópticas mediante correlaciones publicadas (no valores
# inventados por nosotros):
#   - g (SHGC) se aproxima a partir del SHADING-COEF de HULC con el factor
#     0.86 (comprobado directamente contra la interfaz de HULC: para
#     HOR_DC_4-6-6, SHADING-COEF=0.882352941176471 y HULC muestra
#     "Factor Solar (g_gl,n)=0.759" -> 0.759/0.882352941176471=0.860 exacto).
#     HULC no guarda "g" como campo en el .bdc; lo calcula su interfaz con
#     este mismo factor a partir de SHADING-COEF.
#   - solar_tau (Tsol) se calcula con la correlación de Arasteh/Kohler/
#     Griffith en función de SHGC y U (antes se aproximaba solar_tau=g, lo
#     que sobrestima la transmitancia directa en ~8% para nuestro vidrio).
#   - solar_rho (reflectancia) se deriva de Tsol, SHGC y las resistencias de
#     película Ri,s/Ro,s del mismo modelo, con un balance de energía
#     (T+A+R=1, SHGC=T+N*A). La fracción N que fluye hacia el interior se
#     toma como N=Ro,s/(Ri,s+Ro,s) (convención habitual del método, pero esta
#     última fórmula de N no se ha podido verificar palabra por palabra
#     contra el documento fuente original -enlace roto-, así que esta pieza
#     concreta lleva más incertidumbre que las otras dos).
#   - lw_epsilon = 0.84 es la propia constante que fija el modelo LBNL para
#     este caso (vidrio sin más datos), no una invención nuestra.
# Fuente: Arasteh, D., J.C. Kohler, B. Griffith (2009), "Modeling Windows in
# EnergyPlus with Simple Performance Indices", LBNL. Documentado también en
# el Engineering Reference de EnergyPlus, módulo "Window Calculation".


def _propiedades_opticas_lbnl(shgc, u_vidrio):
    """
    Calcula (solar_tau, solar_rho) a partir de (SHGC, U) usando el modelo
    "Simple Glazing System" de Arasteh/Kohler/Griffith (LBNL, 2009), el mismo
    que usa EnergyPlus para convertir U+SHGC en propiedades ópticas completas.

    Fórmulas de Tsol (transmitancia solar a incidencia normal):
        U > 4.5, SHGC < 0.7206:  Tsol = 0.939998*SHGC^2 + 0.20332*SHGC
        U > 4.5, SHGC >= 0.7206: Tsol = 1.30415*SHGC - 0.30515
        U < 3.4, SHGC <= 0.15:   Tsol = 0.41040*SHGC
        U < 3.4, SHGC > 0.15:    Tsol = 0.085775*SHGC^2 + 0.963954*SHGC - 0.084958
        3.4 <= U <= 4.5: interpolación lineal entre los dos casos anteriores.

    Fórmulas de las resistencias de película en verano Ri,s/Ro,s (usadas para
    obtener la fracción de calor absorbido que fluye hacia el interior, N):
        U > 4.5: Ri,s = 1/(29.436546 d^3 - 21.943415 d^2 + 9.945872 d + 7.426151)
                 Ro,s = 1/(2.225824 d + 20.57708)
        U < 3.4: Ri,s = 1/(199.8208128 d^3 - 90.639733 d^2 + 19.737055 d + 6.766575)
                 Ro,s = 1/(5.763355 d + 20.541528)
        donde d = SHGC - Tsol.

    A partir de ahí, con N = Ro,s/(Ri,s+Ro,s) (fracción hacia el interior) y
    el balance de energía Tsol + Asol + Rsol = 1, SHGC = Tsol + N*Asol:
        Asol = (SHGC - Tsol) / N
        Rsol = 1 - Tsol - Asol

    OJO: la fórmula de N usada aquí (N=Ro,s/(Ri,s+Ro,s)) es la convención
    habitual de este tipo de balance térmico, pero no se ha podido verificar
    palabra por palabra contra el documento original de Arasteh/Kohler/
    Griffith (el PDF de LBNL con esa cita ya no está disponible online); por
    tanto solar_rho lleva más incertidumbre que solar_tau, cuyas fórmulas sí
    están verificadas contra el Engineering Reference de EnergyPlus.
    """
    def _tsol(shgc, u):
        def alta(s):  # U > 4.5
            if s < 0.7206:
                return 0.939998 * s**2 + 0.20332 * s
            return 1.30415 * s - 0.30515

        def baja(s):  # U < 3.4
            if s <= 0.15:
                return 0.41040 * s
            return 0.085775 * s**2 + 0.963954 * s - 0.084958

        if u <= 3.4:
            return baja(shgc)
        if u >= 4.5:
            return alta(shgc)
        # interpolación lineal en el rango 3.4-4.5
        t_baja, t_alta = baja(shgc), alta(shgc)
        frac = (u - 3.4) / (4.5 - 3.4)
        return t_baja + frac * (t_alta - t_baja)

    def _resistencias_pelicula(d, u):
        def alta(d):  # U > 4.5
            ri = 1.0 / (29.436546 * d**3 - 21.943415 * d**2 + 9.945872 * d + 7.426151)
            ro = 1.0 / (2.225824 * d + 20.57708)
            return ri, ro

        def baja(d):  # U < 3.4
            ri = 1.0 / (199.8208128 * d**3 - 90.639733 * d**2 + 19.737055 * d + 6.766575)
            ro = 1.0 / (5.763355 * d + 20.541528)
            return ri, ro

        if u <= 3.4:
            return baja(d)
        if u >= 4.5:
            return alta(d)
        ri_b, ro_b = baja(d)
        ri_a, ro_a = alta(d)
        frac = (u - 3.4) / (4.5 - 3.4)
        return (ri_b + frac * (ri_a - ri_b), ro_b + frac * (ro_a - ro_b))

    tsol = _tsol(shgc, u_vidrio)
    tsol = max(0.0, min(shgc, tsol))  # tsol no puede superar shgc físicamente
    d = max(shgc - tsol, 1e-6)
    ri_s, ro_s = _resistencias_pelicula(d, u_vidrio)
    n_interior = ro_s / (ri_s + ro_s)
    asol = d / n_interior
    rsol = 1.0 - tsol - asol
    rsol = max(0.0, min(1.0, rsol))  # acotado a [0,1] por seguridad
    return tsol, rsol


def glass_type_bdl_a_componente(obj):
    """
    Convierte un objeto BDL GLASS-TYPE en un componente "Glazing" de OpenSimula.

    Parámetros de HULC disponibles:
        SHADING-COEF       coeficiente de sombra del vidrio (referido a g=0.86)
        GLASS-CONDUCTANCE  conductancia/transmitancia U del vidrio [W/m²K]

    Mapeo a OpenSimula vía el modelo "Simple Glazing System" de LBNL (ver
    aviso arriba):
        g          = SHADING-COEF * 0.86                    (SHGC)
        solar_tau  = correlación LBNL Tsol(SHGC, U)
        solar_rho  = correlación LBNL Rsol(SHGC, U, Tsol)
        U          = GLASS-CONDUCTANCE
        lw_epsilon = 0.84 (constante del propio modelo LBNL)
    """
    props = obj["props"]

    shading_coef = float(props.get("SHADING-COEF", 1.0))
    u_vidrio = float(props.get("GLASS-CONDUCTANCE", 5.686))

    # Factor solar (SHGC) = SHADING-COEF * 0.86. HULC no guarda "g" en el .bdc;
    # lo calcula su interfaz con este factor 0.86 a partir de SHADING-COEF
    # (verificado contra la propia interfaz: HOR_DC_4-6-6, SHADING-COEF=0.88235
    # -> g=0.759 = 0.88235*0.860). Replicarlo es lo más fiel a HULC.
    g_aprox = shading_coef * 0.86
    g_aprox = max(0.0, min(1.0, g_aprox))  # acotado a [0,1] por seguridad

    solar_tau, solar_rho = _propiedades_opticas_lbnl(g_aprox, u_vidrio)

    componente = {
        "type": "Glazing",
        "name": obj["nombre"],
        "solar_tau": round(solar_tau, 4),
        "g": [round(g_aprox, 4), round(g_aprox, 4)],
        "U": u_vidrio,
        "solar_rho": [round(solar_rho, 4), round(solar_rho, 4)],
        # Emisividad de onda larga del vidrio: 0.84 (valor estándar del vidrio
        # sin capa baja-emisiva, igual que en los casos de validación ASHRAE 140
        # de OpenSimula). Imprescindible para el intercambio radiante interior.
        "lw_epsilon": [0.84, 0.84],
    }
    return componente


def name_frame_bdl_a_componente(obj):
    """
    Convierte un objeto BDL NAME-FRAME (o WINDOW-FRAME) en un componente
    "Frame" de OpenSimula.

    Parámetros de HULC disponibles:
        FRAME-CONDUCT  conductancia del marco [W/m²K], AIRE-AIRE (convención
                       estándar europea EN ISO 10077 para marcos de ventana:
                       incluye las resistencias superficiales interior y
                       exterior, no es un valor superficie-superficie)
        FRAME-ABS      absortividad solar del marco
        FRAME-WIDTH    ancho del marco (no se usa para el Frame en sí)

    OpenSimula pide para Frame:
        thermal_resistance  resistencia térmica SUPERFICIE-SUPERFICIE [m²K/W]
                            (confirmado en la documentación oficial:
                            "Average surface-to-surface thermal resistance
                            of the frame" -component_list_constructions-).
                            OpenSimula añade sus propias películas
                            superficiales (h_cv) durante la simulación.
        solar_alpha         absortividad solar

    El FRAME-CONDUCT de catálogo es aire-aire y OpenSimula añade sus propias
    películas, así que se resta Rsi+Rse=0,17 m²K/W (valor CTE) antes de invertir;
    aplicar R = 1/FRAME-CONDUCT directo duplicaría las resistencias
    superficiales. Detalle en la memoria del TFG (§7.3).
    """
    props = obj["props"]

    u_marco = float(props.get("FRAME-CONDUCT", 5.7))
    abs_marco = float(props.get("FRAME-ABS", 0.8))

    R_SUPERFICIALES_CTE = 0.13 + 0.04  # Rsi + Rse estándar (superficie vertical)

    # Resistencia térmica superficie-superficie: se resta Rsi+Rse del valor
    # aire-aire de HULC. Se acota a un mínimo pequeño positivo por seguridad
    # (evita 0 o negativo si algún marco del catálogo tuviera una FRAME-CONDUCT
    # muy alta, aunque no ocurre en este proyecto).
    if u_marco > 0:
        resistencia = round(max(1.0 / u_marco - R_SUPERFICIALES_CTE, 0.01), 4)
    else:
        resistencia = 0.2

    componente = {
        "type": "Frame",
        "name": obj["nombre"],
        "thermal_resistance": resistencia,
        "solar_alpha": [abs_marco, abs_marco],
    }
    return componente


def _frame_conduct_por_gap(objetos):
    """Lee de los objetos WINDOW el FRAME-CONDUCT (y FRAME-ABS) EFECTIVO que
    HULC calcula para cada hueco.

    En el GAP, el marco es el de biblioteca (NAME-FRAME: madera, metal...). Pero
    HULC, al montar cada ventana, calcula un "marco equivalente" que agrupa:
    marco real + puente térmico del intercalario (separador entre vidrios,
    UNE-EN ISO 10077-1) + el `porcentajeIncrementoU` del GAP. Ese valor lo
    guarda en cada objeto WINDOW como FRAME-CONDUCT (p. ej. 9.224 W/m²K en el
    edificio ATECYR, frente a los 2.0 del marco de madera del GAP).

    CONVENCIÓN — este valor NO es aire-aire (a diferencia del FRAME-CONDUCT del
    catálogo NAME-FRAME, que sí lo es y al que name_frame_bdl_a_componente le
    resta Rsi+Rse). Se comprueba con su magnitud: 9.224 > 1/(Rsi+Rse) = 1/0,17
    = 5,88 W/m²K, que es el máximo físico de una U aire-aire (solo se alcanza
    si el elemento tiene R=0). Restarle 0,17 antes de invertir daría negativo
    (1/9,224 - 0,17 = -0,06). Es una conductancia superficie-superficie / sin
    películas estándar, que OpenSimula ya añade aparte -> se convierte con
    R = 1/FRAME-CONDUCT directo, SIN restar nada.

    Devuelve {nombre_GAP: (frame_conduct, frame_abs)} solo para los GAP cuyas
    ventanas dan un FRAME-CONDUCT coherente entre sí.
    """
    from collections import defaultdict
    por_gap = defaultdict(list)
    for o in objetos:
        if o.get("tipo") != "WINDOW":
            continue
        p = o["props"]
        g = p.get("GAP")
        fc = p.get("FRAME-CONDUCT")
        if not g or fc is None:
            continue
        try:
            fc = float(fc)
            fa = float(p.get("FRAME-ABS", 0.7))
        except (TypeError, ValueError):
            continue
        por_gap[g].append((fc, fa))
    salida = {}
    for g, lst in por_gap.items():
        fcs = [x[0] for x in lst]
        if fcs and (max(fcs) - min(fcs)) < 1e-3:   # coherente entre ventanas
            salida[g] = (fcs[0], lst[0][1])
    return salida


def gap_bdl_a_componente(obj):
    """
    Convierte un objeto BDL GAP (tipo de hueco) en un componente
    "Opening_type" de OpenSimula.

    Un GAP referencia:
        GLASS-TYPE  -> el Glazing a usar
        NAME-FRAME  -> el Frame a usar
        PORCENTAGE  -> porcentaje de la superficie ocupada por el MARCO (%)

    En OpenSimula, Opening_type pide:
        glazing          referencia al Glazing
        frame            referencia al Frame
        glazing_fraction fracción de vidrio (0-1)
        frame_fraction   fracción de marco (0-1)

    OJO: en HULC, PORCENTAGE es el porcentaje de MARCO. Por tanto:
        frame_fraction   = PORCENTAGE / 100
        glazing_fraction = 1 - frame_fraction
    """
    props = obj["props"]

    porcentaje_marco = float(props.get("PORCENTAGE", 10.0)) / 100.0
    porcentaje_marco = max(0.0, min(1.0, porcentaje_marco))

    componente = {
        "type": "Opening_type",
        "name": obj["nombre"],
        "glazing": str(props.get("GLASS-TYPE", "not_defined")),
        "frame": str(props.get("NAME-FRAME", "not_defined")),
        "glazing_fraction": round(1.0 - porcentaje_marco, 4),
        "frame_fraction": round(porcentaje_marco, 4),
        # OpenSimula divide el hueco en vidrio + marco + construcción opaca, con
        # construction_fraction = 1 - glazing_fraction - frame_fraction, y exige
        # el parámetro "construction" siempre que esa fracción sea > 0. Por la
        # aritmética de coma flotante, restas como 1 - 0.85 - 0.15 dan un residuo
        # positivo minúsculo (~2.8e-17) en lugar de 0 exacto, lo que hace que
        # OpenSimula reclame una construcción y aborte el check aunque en la
        # práctica no haya parte opaca. Como no podemos evitar ese residuo (lo
        # genera la resta interna de OpenSimula), asignamos SIEMPRE una
        # construcción de referencia para la parte opaca del hueco; su fracción
        # real es ~0 en todos los casos de este proyecto, incluidas las puertas
        # ciegas (frame_fraction=1, glazing_fraction=0): ahí la hoja opaca de la
        # puerta la representa por completo el "Frame" (con su resistencia
        # térmica y absortividad reales, sacadas de FRAME-CONDUCT/FRAME-ABS), no
        # esta construcción de relleno. Es razonable: según la propia
        # documentación de OpenSimula, la parte de "construction" de un
        # Opening_type también se calcula en régimen estacionario, igual que el
        # Frame, así que no se pierde inercia térmica por elegir uno u otro.
        "construction": _CONSTRUCCION_HUECO_OPACO,
    }
    return componente


# ===========================================================================
# 3 bis. LECTURA DE LA BIBLIOTECA DE MATERIALES DE HULC (BDCatalogo.bdc)
# ===========================================================================

def _normalizar_espacios(nombre):
    """
    Colapsa cualquier secuencia de espacios en uno solo y recorta los
    extremos. HULC no es consistente entre sus propios ficheros: el mismo
    material puede tener un nombre con espacio simple en el .ctehexml del
    proyecto y espacio doble en BDCatalogo.bdc (o viceversa), por ejemplo
    "Tabicón de LH doble [60 mm..." frente a "Tabicón de LH doble  [60 mm...".
    Se usa solo como criterio de búsqueda de respaldo, nunca para decidir el
    nombre final del componente (ese se mantiene tal cual aparece en la
    referencia del .ctehexml, para que siga cuadrando con lo que apunta la
    Construction/Opening_type correspondiente).
    """
    return " ".join(nombre.split())


def _buscar_en_biblioteca(nombre, diccionario, indice_normalizado):
    """
    Busca `nombre` en `diccionario` (biblioteca ya cargada). Primero por
    coincidencia exacta; si falla, por nombre con espacios normalizados
    usando `indice_normalizado` ({nombre_normalizado: nombre_original}).
    Devuelve el componente encontrado (dict) o None.
    """
    if nombre in diccionario:
        return diccionario[nombre]
    nombre_norm = _normalizar_espacios(nombre)
    original = indice_normalizado.get(nombre_norm)
    if original is not None:
        return diccionario[original]
    return None


def leer_biblioteca_materiales(ruta_bdc):
    """
    Lee la biblioteca de HULC (archivo BDCatalogo.bdc) y devuelve TRES
    diccionarios, uno por cada tipo de componente que sabemos resolver:

        (materiales, vidrios, marcos)

    donde cada uno es {nombre: componente_OpenSimula}.

    Este archivo está en formato BDL, igual que la sección EntradaGraficaLIDER
    del .ctehexml, así que reutilizamos el mismo parser. La diferencia es la
    codificación: el .bdc viene en ISO-8859-1 (Latin-1), no en UTF-8.

    Por qué hace falta: el .ctehexml del proyecto a menudo solo guarda los
    NOMBRES de materiales, vidrios y marcos que proceden de la biblioteca, sin
    sus propiedades físicas. Esta biblioteca las aporta, enlazando por el
    nombre exacto.
    """
    # OJO: codificación Latin-1, no UTF-8 (lo detectamos con el comando 'file').
    with open(ruta_bdc, "r", encoding="ISO-8859-1") as f:
        texto = f.read()

    objetos = parsear_objetos_bdl(texto)

    materiales = {}
    vidrios = {}
    marcos = {}
    for obj in objetos:
        if obj["tipo"] == "MATERIAL":
            materiales[obj["nombre"]] = material_bdl_a_componente(obj)
        elif obj["tipo"] == "GLASS-TYPE":
            vidrios[obj["nombre"]] = glass_type_bdl_a_componente(obj)
        elif obj["tipo"] in ("NAME-FRAME", "WINDOW-FRAME"):
            marcos[obj["nombre"]] = name_frame_bdl_a_componente(obj)
    return materiales, vidrios, marcos


# ===========================================================================
# 4. FUNCIÓN PRINCIPAL: ctehexml -> diccionario OpenSimula
# ===========================================================================

def ctehexml_a_diccionario(ruta, nombre_proyecto=None, ruta_biblioteca=None,
                           incluir_geometria=False,
                           archivo_met=None, tipo_met="MET",
                           incluir_hvac=False,
                           infiltracion=None, carga_interna_W_m2=4.4,
                           ventilacion_renh=None,
                           usar_horarios_cte=False,
                           incluir_unconditioned=False,
                           usar_frame_conduct_hueco=True,
                           aplanar_cubierta=False,
                           muros_verticales_underground=True,
                           signo_azimut_edificio=1):
    """
    Función principal del módulo.

    Lee un archivo .ctehexml de HULC y devuelve un diccionario con el formato
    de proyecto de OpenSimula (apto para Project.read_dict()), conteniendo en
    esta Fase 1 los componentes Material y Construction.

    Parámetros
    ----------
    ruta : str
        Ruta al archivo .ctehexml.
    nombre_proyecto : str, opcional
        Nombre para el proyecto OpenSimula. Si es None, se toma del propio
        archivo (etiqueta <nomPro>).
    ruta_biblioteca : str, opcional
        Ruta al archivo BDCatalogo.bdc (biblioteca de materiales de HULC).
        Si se indica, los materiales que el .ctehexml referencia solo por
        nombre se completan con sus propiedades físicas tomadas de esta
        biblioteca. Si es None, esos materiales quedan sin definir (y se
        listan en el informe).
    infiltracion, ventilacion_renh : float o None, por defecto None
        Renovaciones de aire por hora (ren/h) de infiltración y de ventilación
        higiénica. Solo se usan en los espacios cuyo INF-METHOD es CRACK (los
        que HULC no aplica literal). Con None (recomendado) se calculan a
        partir de los propios datos del .ctehexml, reproduciendo el desglose
        del informe HE-1 de HULC:
          - ventilacion_renh = INF-FLOW ponderado por PERCENTAGE-AIR-CHANGES
            entre el volumen habitable:
            (p0*|INF-FLOW[0]| + p1*|INF-FLOW[1]|)/(p0+p1) / V. Si no hay
            INF-FLOW se usa <valorImpulsionAire> (l/s -> m3/h) / V.
          - infiltracion = <ValorN50Medido>/20 si hay ensayo de permeabilidad;
            si no, el AIR-CHANGES/HR de la SPACE-CONDITIONS (referencia n50 de
            INF-METHOD=CRACK) dividido por 20; si tampoco, 0,33 ren/h con aviso.
        Pasar un número fuerza ese valor (para pruebas de sensibilidad).
    incluir_unconditioned : bool, por defecto False
        Si es False, solo los espacios TYPE=CONDITIONED de HULC reciben un
        HVAC_perfect_system (y por tanto aportan demanda). Los
        TYPE=UNCONDITIONED y TYPE=UNHABITED flotan, igual que en HULC.
        Poner True solo para diagnóstico.
    usar_frame_conduct_hueco : bool, por defecto True
        Si es True, cuando el FRAME-CONDUCT que HULC guarda en un objeto WINDOW
        es MAYOR que el del marco de catálogo (porque HULC le ha sumado el
        puente del intercalario y el porcentajeIncrementoU), se genera un Frame
        propio del hueco con ese valor efectivo (R = 1/FRAME-CONDUCT, sin
        restar películas: no es un valor aire-aire). Si el WINDOW solo copia el
        FRAME-CONDUCT del catálogo (puertas ciegas, sin intercalario), no se
        toca nada.
    aplanar_cubierta : bool, por defecto False
        NO usar en la conversión normal: falsea la geometría. Sustituye la
        cubierta inclinada real (varias aguas) por un techo plano equivalente.
        Es solo una herramienta de DIAGNÓSTICO: se añadió para aislar el
        patrón del fallo de factores de forma de OpenSimula (comparar el
        espacio bajo-cubierta con y sin faldones). El conversor de producción
        traslada la cubierta tal como la define HULC.
    muros_verticales_underground : bool, por defecto True
        Con True se respeta la clasificación de HULC: los muros que el
        .ctehexml declara como UNDERGROUND-WALL (muretes de cámara sanitaria,
        muros contra terreno...) se generan como UNDERGROUND aunque sean
        verticales. Con False (solo diagnóstico) esos muros verticales se
        reclasifican a EXTERIOR -reciben sol y aire exterior que HULC no les
        aplica-, para no pasar por la ISO 13370 de OpenSimula sobre
        superficies verticales. Las soleras horizontales van UNDERGROUND en
        ambos casos.

    Devuelve
    --------
    (dict, dict)
        - El diccionario de proyecto de OpenSimula.
        - Un diccionario de "informe" con avisos útiles (materiales resueltos
          desde la biblioteca, materiales que siguen sin definir, etc.).
    """
    texto_xml = leer_ctehexml(ruta)

    # --- Cabecera XML ---
    datos_generales = extraer_datos_generales(texto_xml)

    # --- Bloque BDL ---
    texto_bdl = extraer_bloque_bdl(texto_xml)
    objetos = parsear_objetos_bdl(texto_bdl)

    # --- Filtramos por tipo y convertimos ---
    componentes = []
    nombres_materiales_definidos = set()

    for obj in objetos:
        if obj["tipo"] == "MATERIAL":
            comp = material_bdl_a_componente(obj)
            componentes.append(comp)
            nombres_materiales_definidos.add(comp["name"])

    construcciones = []
    # Mapa nombre_construccion_base -> ABSORPTANCE real, extraído de los
    # objetos EXTERIOR-WALL/ROOF/UNDERGROUND-WALL (el dato vive ahí, no en el
    # objeto LAYERS). Si una misma construcción base la usan varios muros con
    # ABSORPTANCE distinto, se avisa y se usa el primero encontrado (no debería
    # pasar en un proyecto bien formado de HULC, pero se comprueba en vez de
    # asumirlo).
    absortancia_por_construccion = {}
    avisos_absortancia = []
    for obj in objetos:
        if obj["tipo"] in ("EXTERIOR-WALL", "ROOF", "UNDERGROUND-WALL"):
            p = obj["props"]
            if "ABSORPTANCE" not in p:
                continue
            base = p.get("CONSTRUCCION_MURO", p.get("CONSTRUCTION", ""))
            valor = float(p["ABSORPTANCE"])
            if base in absortancia_por_construccion:
                if abs(absortancia_por_construccion[base] - valor) > 1e-6:
                    avisos_absortancia.append(
                        f"{base}: {absortancia_por_construccion[base]} vs {valor} "
                        f"(en {obj['nombre']})")
            else:
                absortancia_por_construccion[base] = valor
    if avisos_absortancia:
        print("AVISO: ABSORPTANCE distinta para la misma construcción base:")
        for a in avisos_absortancia:
            print("  ", a)

    for obj in objetos:
        if obj["tipo"] == "LAYERS":
            construcciones.append(construccion_bdl_a_componente(
                obj, absortancia_por_construccion.get(obj["nombre"])))

    # --- FASE 2: Huecos (vidrios, marcos y tipos de hueco) ---
    # Vidrios (GLASS-TYPE -> Glazing) y marcos (NAME-FRAME -> Frame) primero,
    # porque los Opening_type los referencian por nombre.
    vidrios = []
    marcos = []
    tipos_hueco = []
    for obj in objetos:
        if obj["tipo"] == "GLASS-TYPE":
            vidrios.append(glass_type_bdl_a_componente(obj))
        elif obj["tipo"] in ("NAME-FRAME", "WINDOW-FRAME"):
            marcos.append(name_frame_bdl_a_componente(obj))
        elif obj["tipo"] == "GAP":
            tipos_hueco.append(gap_bdl_a_componente(obj))

    # --- Referencias que apuntan a elementos NO definidos en el .ctehexml
    #     (proceden de la biblioteca de HULC) ---
    # Materiales referenciados por las construcciones:
    materiales_referenciados = set()
    for c in construcciones:
        for nombre_mat in c["materials"]:
            materiales_referenciados.add(nombre_mat)
    mat_faltantes = materiales_referenciados - nombres_materiales_definidos

    # Vidrios y marcos referenciados por los tipos de hueco:
    nombres_vidrios_def = {v["name"] for v in vidrios}
    nombres_marcos_def = {m["name"] for m in marcos}
    vidrios_ref = {h["glazing"] for h in tipos_hueco}
    marcos_ref = {h["frame"] for h in tipos_hueco}
    vid_faltantes = vidrios_ref - nombres_vidrios_def
    mar_faltantes = marcos_ref - nombres_marcos_def

    # --- Resolución de los faltantes con la biblioteca BDCatalogo.bdc ---
    resueltos_desde_biblioteca = []
    no_resueltos = sorted(mat_faltantes | vid_faltantes | mar_faltantes)

    if ruta_biblioteca is not None and (mat_faltantes or vid_faltantes or mar_faltantes):
        bib_mat, bib_vid, bib_mar = leer_biblioteca_materiales(ruta_biblioteca)
        # Índices por nombre normalizado (espacios colapsados), para resolver
        # referencias que difieren solo en espacios respecto a la biblioteca.
        idx_mat = {_normalizar_espacios(n): n for n in bib_mat}
        idx_vid = {_normalizar_espacios(n): n for n in bib_vid}
        idx_mar = {_normalizar_espacios(n): n for n in bib_mar}
        no_resueltos = []

        # Materiales
        for nombre in sorted(mat_faltantes):
            comp = _buscar_en_biblioteca(nombre, bib_mat, idx_mat)
            if comp is not None:
                comp = dict(comp)
                comp["name"] = nombre  # respeta el nombre tal como se referencia
                componentes.append(comp)
                nombres_materiales_definidos.add(nombre)
                resueltos_desde_biblioteca.append(("Material", nombre))
            else:
                no_resueltos.append(nombre)
        # Vidrios
        for nombre in sorted(vid_faltantes):
            comp = _buscar_en_biblioteca(nombre, bib_vid, idx_vid)
            if comp is not None:
                comp = dict(comp)
                comp["name"] = nombre
                vidrios.append(comp)
                resueltos_desde_biblioteca.append(("Glazing", nombre))
            else:
                no_resueltos.append(nombre)
        # Marcos
        for nombre in sorted(mar_faltantes):
            comp = _buscar_en_biblioteca(nombre, bib_mar, idx_mar)
            if comp is not None:
                comp = dict(comp)
                comp["name"] = nombre
                marcos.append(comp)
                resueltos_desde_biblioteca.append(("Frame", nombre))
            else:
                no_resueltos.append(nombre)

    # Orden de la lista de componentes (por legibilidad y por dependencias):
    #   materiales -> vidrios -> marcos -> construcciones -> tipos de hueco
    # Los Opening_type van al final porque referencian Glazing y Frame.

    # Construcción para la parte OPACA de los huecos (hoja de puerta ciega y el
    # residuo de coma flotante de las fracciones). Se genera siempre porque
    # todos los Opening_type la referencian. Es una hoja de puerta estándar:
    # tablero de madera de ~4 cm (U ≈ 2 W/m²K, valor habitual de puerta opaca).
    if not any(m.get("name") == "MADERA_PUERTA_OPACA"
               for m in componentes if m.get("type") == "Material"):
        componentes.append({
            "type": "Material", "name": "MADERA_PUERTA_OPACA",
            "conductivity": 0.18, "density": 600, "specific_heat": 1600,
        })
    construcciones.append({
        "type": "Construction", "name": _CONSTRUCCION_HUECO_OPACO,
        "materials": ["MADERA_PUERTA_OPACA"], "thicknesses": [0.04],
        "solar_alpha": [0.6, 0.6], "lw_epsilon": [0.9, 0.9],
    })

    # --- Marco efectivo del hueco (FRAME-CONDUCT por objeto WINDOW) ---
    # HULC guarda en cada WINDOW un FRAME-CONDUCT. Puede ser:
    #   (a) una COPIA del FRAME-CONDUCT del marco de catálogo (GAP -> NAME-FRAME),
    #       cuando no hay puente del intercalario ni porcentajeIncrementoU
    #       (p. ej. puertas ciegas). En ese caso NO se toca nada: vale el Frame
    #       de catálogo que ya generó name_frame_bdl_a_componente(), con su
    #       resta de Rsi+Rse (es un valor AIRE-AIRE, EN ISO 10077).
    #   (b) un valor RECALCULADO por HULC que agrupa marco + puente del
    #       intercalario + porcentajeIncrementoU. Se detecta porque es MAYOR que
    #       el del catálogo. Ese valor recalculado NO es aire-aire (p. ej. 9.224
    #       en ATECYR > 1/0,17 = 5,88, el techo físico de una U aire-aire): es
    #       una conductancia superficie-superficie -> R = 1/FRAME-CONDUCT SIN
    #       restar nada. Se genera un Frame propio del hueco.
    if usar_frame_conduct_hueco:
        fc_por_gap = _frame_conduct_por_gap(objetos)
        for ot in tipos_hueco:
            info = fc_por_gap.get(ot["name"])
            if info is None:
                continue
            fc, fa = info
            if fc <= 0:
                continue
            marco_actual = next((m for m in marcos if m["name"] == ot["frame"]), None)
            r_actual = marco_actual.get("thermal_resistance") if marco_actual else None
            # FRAME-CONDUCT aire-aire del catálogo, reconstruido de su R
            # superficie-superficie (name_frame_bdl_a_componente restó 0,17).
            fc_catalogo = (1.0 / (r_actual + 0.17)
                           if (r_actual is not None and r_actual > 0) else 0.0)
            # Solo caso (b): el valor por ventana supera al del catálogo.
            if fc <= fc_catalogo + 0.05:
                continue
            r_nuevo = max(round(1.0 / fc, 4), 0.005)   # sin resta; suelo defensivo
            nuevo_nombre = f"{ot['name']}__MARCO_HULC"
            if not any(m["name"] == nuevo_nombre for m in marcos):
                marcos.append({
                    "type": "Frame",
                    "name": nuevo_nombre,
                    "thermal_resistance": r_nuevo,
                    "solar_alpha": [round(fa, 4), round(fa, 4)],
                })
            ot["frame"] = nuevo_nombre

    componentes.extend(vidrios)
    componentes.extend(marcos)
    componentes.extend(construcciones)
    componentes.extend(tipos_hueco)

    # --- Montaje del diccionario de proyecto ---
    if nombre_proyecto is None:
        nombre_proyecto = datos_generales.get("nomPro", "Proyecto importado de HULC")

    # --- FASE 3: Geometría (opcional) ---
    # Si se pide, añadimos Building, Space, Building_surface y Opening usando
    # el módulo hulc_geometria. Se importa aquí dentro para no crear una
    # dependencia obligatoria (las fases 1-2 funcionan sin el módulo).
    n_geom = {}
    if incluir_geometria:
        try:
            import hulc_geometria as geo
            arbol = geo.parsear_arbol_bdl(texto_bdl)
            plantas = geo.extraer_geometria(arbol)
            # Cargas internas REALES declaradas en el .ctehexml (objetos
            # SPACE-CONDITIONS: ocupación, iluminación, equipos, infiltración).
            # Con esto el modelo usa las mismas cargas que HULC en lugar de un
            # perfil genérico.
            conds = geo._extraer_space_conditions(arbol)
            # Horarios REALES de esas condiciones (SCHEDULE-PD ->
            # Year/Week/Day_schedule). Así las cargas siguen el perfil horario
            # de HULC (laboral/no laboral, periodos de verano...) en vez de uno
            # genérico.
            # Condiciones de los sistemas (consignas, funcionamiento y
            # temporada calefacción/refrigeración), también del archivo.
            sys_conds = geo._extraer_system_conditions(arbol)
            sys_por_esp = geo._extraer_system_conditions_por_espacio(arbol)
            nombres_horarios = set()
            for c in conds.values():
                for k in ("people_schedule", "lighting_schedule",
                          "equip_schedule", "inf_schedule"):
                    if c.get(k):
                        nombres_horarios.add(c[k])
            for c in sys_conds.values():
                for k in ("heat_temp_sch", "cool_temp_sch", "heating_schedule",
                          "cooling_schedule", "season_sch"):
                    if c.get(k):
                        nombres_horarios.add(c[k])
            comps_horarios, horarios_map = geo._traducir_horarios(
                arbol, sorted(nombres_horarios))
            # Espesor total (suma de 'thicknesses') de cada Construction ya
            # traducida, para poder dar a exterior_perimeter_wall_thickness de
            # las soleras UNDERGROUND el espesor REAL del muro perimetral en
            # vez del valor por defecto de OpenSimula (0.3 m).
            espesores_construcciones = {
                c["name"]: round(sum(c.get("thicknesses", [])), 4)
                for c in construcciones if c.get("thicknesses")
            }

            # Datos de infiltración y ventilación higiénica que trae el
            # .ctehexml (para que geometria_a_componentes calcule las ren/h de
            # los espacios INF-METHOD=CRACK sin fijarlas a mano):
            #  - <valorImpulsionAire>  : caudal de impulsión HS3 en l/s.
            #  - <ValorN50Medido>      : n50 de ensayo de puerta soplante
            #    (0 si <ensayoPermeabilidad> = NO).
            #  - BUILD-PARAMETERS.INF-FLOW : par (base, punta) en m3/h de la
            #    infiltración que calcula HULC; se toma el primer valor.
            #  - BUILD-PARAMETERS.PERCENTAGE-AIR-CHANGES : par (h base, h punta)
            #    con que HULC pondera INF-FLOW a lo largo del día.
            #  - SYSTEM-CONDITIONS.RECOV-EFF : rendimiento del recuperador de
            #    calor de la ventilación (0 si no hay). Es el campo que usa el
            #    motor DOE-2 de HULC; coincide con <recuperacionCalor> del XML.
            def _num(x, defecto=0.0):
                try:
                    return float(str(x).strip())
                except (TypeError, ValueError):
                    return defecto
            caudal_impulsion_m3h = _num(datos_generales.get("valorImpulsionAire")) * 3.6
            n50_medido = _num(datos_generales.get("ValorN50Medido")) or None
            recuperador_calor = 0.0
            inf_flow = None
            pct_air_changes = None
            for obj in objetos:
                if obj["tipo"] == "BUILD-PARAMETERS":
                    v = obj["props"].get("INF-FLOW")
                    if isinstance(v, list):
                        inf_flow = [abs(_num(x)) for x in v]
                    elif v is not None:
                        inf_flow = [abs(_num(v))]
                    p = obj["props"].get("PERCENTAGE-AIR-CHANGES")
                    if isinstance(p, list):
                        pct_air_changes = [_num(x) for x in p]
                    elif p is not None:
                        pct_air_changes = [_num(p)]
                elif obj["tipo"] == "SYSTEM-CONDITIONS":
                    eff = _num(obj["props"].get("RECOV-EFF", 0.0))
                    if eff > recuperador_calor:
                        recuperador_calor = eff

            comps_geo = geo.geometria_a_componentes(
                plantas,
                incluir_hvac=incluir_hvac,
                infiltracion=infiltracion,
                ventilacion_renh=ventilacion_renh,
                caudal_impulsion_m3h=caudal_impulsion_m3h or None,
                inf_flow=inf_flow,
                pct_air_changes=pct_air_changes,
                n50_medido=n50_medido,
                recuperador_calor=recuperador_calor,
                carga_interna_W_m2=carga_interna_W_m2,
                usar_horarios_cte=usar_horarios_cte,
                aplanar_cubierta=aplanar_cubierta,
                muros_verticales_underground=muros_verticales_underground,
                space_conditions=conds,
                horarios_map=horarios_map,
                componentes_horarios=comps_horarios,
                system_conditions=sys_conds,
                system_conditions_por_espacio=sys_por_esp,
                incluir_unconditioned=incluir_unconditioned,
                espesores_construcciones=espesores_construcciones)

            # Las superficies UNDERGROUND apuntan a una construcción con nombre
            # único "<base>__<superficie>". Creamos esas copias a partir de la
            # construcción base (que ya está en 'construcciones'), porque
            # OpenSimula MODIFICA cada construcción UNDERGROUND al añadir la
            # capa de terreno (le añade un material y un espesor a las listas
            # "materials"/"thicknesses"). OJO: tiene que ser una copia
            # PROFUNDA. Con un dict(original) superficial, "materials" y
            # "thicknesses" siguen siendo las MISMAS listas (mismo id) que la
            # construcción base y que cualquier otra copia derivada de ella.
            # Si dos superficies UNDERGROUND comparten construcción base (caso
            # habitual: varias soleras usan la misma "LAYERS" de HULC), la capa
            # de terreno que OpenSimula añade a la primera se cuela en la
            # segunda al compartir lista, dejándola con más materiales que
            # espesores -> IndexError al calcular la resistencia térmica.
            import copy as _copy
            base_por_nombre = {c["name"]: c for c in construcciones}
            copias = []
            for comp in comps_geo:
                if (comp.get("type") == "Building_surface"
                        and comp.get("surface_type") == "UNDERGROUND"):
                    nombre_copia = comp.get("construction", "")
                    if "__" in nombre_copia:
                        base = nombre_copia.split("__", 1)[0]
                        if base in base_por_nombre:
                            original = base_por_nombre[base]
                            nueva = _copy.deepcopy(original)
                            nueva["name"] = nombre_copia
                            copias.append(nueva)
            # Insertamos las copias antes de la geometría (deben existir cuando
            # las superficies las referencian).
            componentes.extend(copias)
            componentes.extend(comps_geo)
            from collections import Counter
            n_geom = dict(Counter(c["type"] for c in comps_geo))
            n_geom["Construction_underground_copias"] = len(copias)
        except ImportError:
            n_geom = {"error": "no se encontró el módulo hulc_geometria.py"}

    # --- Clima (archivo meteorológico) ---
    # OpenSimula necesita un componente File_met y que el proyecto lo referencie
    # mediante el parámetro "simulation_file_met". Solo se añade si se indica un
    # archivo. El nombre del componente lo usamos como referencia.
    nombre_met = None
    if archivo_met is not None:
        import os
        nombre_met = os.path.splitext(os.path.basename(archivo_met))[0]
        componentes.append({
            "type": "File_met",
            "name": nombre_met,
            "file_type": tipo_met,        # "MET" o "TMY3"
            "file_name": archivo_met,
        })

    # --- Corrección de norte geográfico (BUILD-PARAMETERS.AZIMUTH) ---
    # HULC da el azimut de cada muro en coordenadas LOCALES del proyecto;
    # BUILD-PARAMETERS.AZIMUTH (uno por proyecto, distinto del AZIMUTH de cada
    # muro) es el giro que alinea ese sistema local con el norte real y decide
    # qué orientación recibe el sol cada fachada. Es una rotación rígida de todo
    # el edificio: se suma al azimut de cada superficie Y se rota su ref_point
    # el mismo ángulo (rotar el azimut sin mover ref_point deshace el edificio
    # en 3D). x_polygon/y_polygon y width/height son locales y no cambian.
    azimut_edificio = 0.0
    for obj in objetos:
        if obj["tipo"] == "BUILD-PARAMETERS":
            azimut_edificio = float(obj["props"].get("AZIMUTH", 0.0)) * signo_azimut_edificio
            break
    if azimut_edificio:
        theta = math.radians(azimut_edificio)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        for c in componentes:
            if c.get("type") != "Building_surface":
                continue
            if "azimuth" in c:
                c["azimuth"] = round(
                    ((c["azimuth"] + azimut_edificio + 180.0) % 360.0) - 180.0, 4)
            if "ref_point" in c and c["ref_point"] is not None:
                x0, y0, z0 = c["ref_point"]
                x1 = x0 * cos_t - y0 * sin_t
                y1 = x0 * sin_t + y0 * cos_t
                c["ref_point"] = [round(x1, 4), round(y1, 4), z0]

    proyecto = {
        "name": nombre_proyecto,
        "time_step": 3600,
        "n_time_steps": 8760,
        "initial_time": "01/01/2001 00:00:00",
        "components": componentes,
    }
    if nombre_met is not None:
        proyecto["simulation_file_met"] = nombre_met

    informe = {
        "zona_climatica": datos_generales.get("zonaClimatica", "?"),
        "provincia": datos_generales.get("provincia", "?"),
        "n_materiales_en_archivo": len(
            [c for c in componentes if c["type"] == "Material"]
        ),
        "n_construcciones": len(construcciones),
        "n_vidrios": len(vidrios),
        "n_marcos": len(marcos),
        "n_tipos_hueco": len(tipos_hueco),
        "componentes_geometria": n_geom,
        "materiales_resueltos_desde_biblioteca": resueltos_desde_biblioteca,
        "materiales_sin_resolver": no_resueltos,
    }

    return proyecto, informe


# ===========================================================================
# 5. USO DESDE LÍNEA DE COMANDOS / DEMO
# ===========================================================================

if __name__ == "__main__":
    import sys
    import json
    import pprint

    if len(sys.argv) < 2:
        print("Uso: python hulc_to_opensimula.py archivo.ctehexml [BDCatalogo.bdc]")
        sys.exit(1)

    # Segundo argumento opcional: la biblioteca de materiales.
    ruta_bib = sys.argv[2] if len(sys.argv) > 2 else None

    proyecto, informe = ctehexml_a_diccionario(sys.argv[1], ruta_biblioteca=ruta_bib)

    print("=" * 70)
    print("INFORME DE CONVERSIÓN")
    print("=" * 70)
    print(f"Zona climática:                  {informe['zona_climatica']}")
    print(f"Provincia:                       {informe['provincia']}")
    print(f"Materiales en el proyecto:       {informe['n_materiales_en_archivo']}")
    print(f"Construcciones:                  {informe['n_construcciones']}")
    print(f"Vidrios (Glazing):               {informe['n_vidrios']}")
    print(f"Marcos (Frame):                  {informe['n_marcos']}")
    print(f"Tipos de hueco (Opening_type):   {informe['n_tipos_hueco']}")
    print(f"Elementos resueltos desde la biblioteca: "
          f"{len(informe['materiales_resueltos_desde_biblioteca'])}")
    for tipo, m in informe["materiales_resueltos_desde_biblioteca"]:
        print(f"    + [{tipo}] {m}")
    print(f"Elementos SIN resolver:          "
          f"{len(informe['materiales_sin_resolver'])}")
    for m in informe["materiales_sin_resolver"]:
        print(f"    - {m}")

    print()
    print("=" * 70)
    print("DICCIONARIO DE PROYECTO OPENSIMULA (primeros componentes)")
    print("=" * 70)
    # Mostramos solo una muestra para no saturar la consola.
    muestra = dict(proyecto)
    muestra["components"] = proyecto["components"][:4]
    pprint.pprint(muestra, sort_dicts=False, width=100)
    print(f"... ({len(proyecto['components'])} componentes en total)")
