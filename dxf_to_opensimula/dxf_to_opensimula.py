"""
dxf_to_opensimula.py
Extrae polígonos de planta de un DXF (una LWPOLYLINE por capa = un Space)
y genera componentes OpenSimula con detección automática de paredes interiores.

Uso:
    python dxf_to_opensimula.py P2.dxf --height 3.0
    python dxf_to_opensimula.py P2.dxf --height 3.0 --z_floor 3.0 --building edificio
    python dxf_to_opensimula.py P2.dxf --height 3.0 --output components.py
    python dxf_to_opensimula.py P2.dxf --list-layers
"""

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path

try:
    import ezdxf
except ImportError:
    sys.exit("Instala ezdxf:  pip install ezdxf")


# ── Geometría ──────────────────────────────────────────────────────────────────

def polygon_signed_area(pts):
    n = len(pts)
    a = 0.0
    for i in range(n):
        j = (i + 1) % n
        a += pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1]
    return a / 2.0


def ensure_ccw(pts):
    """Devuelve el polígono en sentido antihorario (normales exteriores correctas)."""
    return pts[::-1] if polygon_signed_area(pts) < 0 else pts


def wall_length(p1, p2):
    return round(math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2), 6)


def wall_azimuth_ccw(p1, p2):
    """
    Azimuth OpenSimula para un segmento p1→p2 de un polígono CCW.
    La normal exterior (lado 0) es la normal derecha del segmento.
    Convención: 0=sur, 90=este, 180=norte, −90=oeste.
    """
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    nx, ny = dy, -dx
    L = math.sqrt(nx**2 + ny**2)
    return round(math.degrees(math.atan2(nx/L, -ny/L)), 1)


def seg_key(p1, p2):
    """Clave canónica de un segmento (independiente de orientación)."""
    return tuple(sorted([
        (round(p1[0], 3), round(p1[1], 3)),
        (round(p2[0], 3), round(p2[1], 3)),
    ]))


# ── Lectura del DXF ────────────────────────────────────────────────────────────

def read_spaces(dxf_path, layers=None):
    """
    Lee el DXF y devuelve un dict {layer_name: [pts CCW]}.
    Solo polilíneas (LWPOLYLINE) de las capas indicadas (o todas).
    """
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    spaces = {}
    for entity in msp:
        if entity.dxftype() != "LWPOLYLINE":
            continue
        name = entity.dxf.layer
        if layers and name not in layers:
            continue
        pts = [(round(float(p[0]), 6), round(float(p[1]), 6))
               for p in entity.get_points()]
        if pts[0] == pts[-1]:
            pts = pts[:-1]
        spaces[name] = ensure_ccw(pts)
    return spaces


def detect_interior_walls(spaces):
    """
    Compara todos los segmentos entre espacios.
    Devuelve un dict: seg_key → [space_name_0, space_name_1]
    para los segmentos compartidos por exactamente dos espacios.

    space_name_0 es el espacio cuyo polígono CCW define la normal
    que apunta hacia el exterior de ese espacio (lado 0 en OpenSimula).
    """
    seg_to_walls = defaultdict(list)   # key → [(space_name, p1, p2)]
    for name, pts in spaces.items():
        n = len(pts)
        for i in range(n):
            p1 = pts[i]
            p2 = pts[(i + 1) % n]
            seg_to_walls[seg_key(p1, p2)].append((name, p1, p2))

    interior = {}
    for key, walls in seg_to_walls.items():
        if len(walls) == 2:
            # walls[0]: space_0 (normal exterior = normal derecha CCW del seg)
            # walls[1]: space_1 (normal apunta al revés)
            interior[key] = [walls[0][0], walls[1][0]]
    return interior


# ── Generador de componentes ───────────────────────────────────────────────────

def extract_components(dxf_path, height=3.0, z_floor=0.0,
                       building="edificio", layers=None):
    """
    Genera la lista de componentes OpenSimula:
      - Space por cada capa
      - Building_surface RECTANGLE por cada pared (EXTERIOR o INTERIOR)
      - Building_surface POLYGON para cubierta (EXTERIOR)
      - Building_surface POLYGON para solera  (UNDERGROUND)
    """
    spaces = read_spaces(dxf_path, layers)
    interior_walls = detect_interior_walls(spaces)

    MIN_LENGTH = 0.01   # ignorar segmentos degenerados

    components = []

    for name, pts in sorted(spaces.items()):
        area = round(abs(polygon_signed_area(pts)), 4)
        volume = round(area * height, 4)

        # ── Space ──────────────────────────────────────────────────────────
        components.append({
            "type": "Space",
            "name": name,
            "building": building,
            "spaces_type": "not_defined",
            "floor_area": area,
            "volume": volume,
            "furniture_weight": 10,
        })

        # ── Paredes ────────────────────────────────────────────────────────
        n = len(pts)
        wall_idx = 0
        for i in range(n):
            p1 = pts[i]
            p2 = pts[(i + 1) % n]
            L = wall_length(p1, p2)
            if L < MIN_LENGTH:
                continue

            az = wall_azimuth_ccw(p1, p2)
            ref = [round(p1[0], 4), round(p1[1], 4), round(z_floor, 4)]
            key = seg_key(p1, p2)

            if key in interior_walls:
                # Pared compartida: INTERIOR con dos espacios
                side0, side1 = interior_walls[key]
                surf = {
                    "type": "Building_surface",
                    "name": f"{name}_wall_{wall_idx}",
                    "shape": "RECTANGLE",
                    "width": round(L, 4),
                    "height": round(height, 4),
                    "ref_point": ref,
                    "azimuth": az,
                    "altitude": 0,
                    "surface_type": "INTERIOR",
                    "construction": "not_defined",
                    "spaces": [side0, side1],
                }
            else:
                # Pared exterior
                surf = {
                    "type": "Building_surface",
                    "name": f"{name}_wall_{wall_idx}",
                    "shape": "RECTANGLE",
                    "width": round(L, 4),
                    "height": round(height, 4),
                    "ref_point": ref,
                    "azimuth": az,
                    "altitude": 0,
                    "surface_type": "EXTERIOR",
                    "construction": "not_defined",
                    "spaces": [name],
                }
            components.append(surf)
            wall_idx += 1

        # ── Cubierta ──────────────────────────────────────────────────────
        x_poly = [round(p[0], 4) for p in pts]
        y_poly = [round(p[1], 4) for p in pts]
        components.append({
            "type": "Building_surface",
            "name": f"{name}_roof",
            "shape": "POLYGON",
            "x_polygon": x_poly,
            "y_polygon": y_poly,
            "ref_point": [0.0, 0.0, round(z_floor + height, 4)],
            "azimuth": 0,
            "altitude": 90,
            "surface_type": "EXTERIOR",
            "construction": "not_defined",
            "spaces": [name],
        })

        # ── Solera ────────────────────────────────────────────────────────
        components.append({
            "type": "Building_surface",
            "name": f"{name}_floor",
            "shape": "POLYGON",
            "x_polygon": x_poly,
            "y_polygon": y_poly,
            "ref_point": [0.0, 0.0, round(z_floor, 4)],
            "azimuth": 0,
            "altitude": -90,
            "surface_type": "UNDERGROUND",
            "construction": "not_defined",
            "ground_material": "not_defined",
            "spaces": [name],
        })

    return components


def print_summary(spaces, interior_walls):
    """Imprime un resumen legible de la detección."""
    print(f"\n{'─'*55}")
    print(f"  Espacios detectados: {len(spaces)}")
    for name, pts in sorted(spaces.items()):
        area = abs(polygon_signed_area(pts))
        print(f"    {name}: {len(pts)} vértices, {area:.2f} m²")
    print(f"\n  Paredes interiores detectadas: {len(interior_walls)}")
    for key, (s0, s1) in sorted(interior_walls.items(), key=lambda x: str(x)):
        p1, p2 = key
        L = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        print(f"    {s0} ↔ {s1}  L={L:.3f} m")
    print(f"{'─'*55}\n")


# ── Serialización ──────────────────────────────────────────────────────────────

def format_value(v):
    if isinstance(v, str):
        return f'"{v}"'
    elif isinstance(v, list):
        inner = ", ".join(
            f'"{x}"' if isinstance(x, str) else str(x)
            for x in v
        )
        return f"[{inner}]"
    else:
        return str(v)


def format_component(comp, indent=8):
    pad  = " " * indent
    inner = " " * (indent + 4)
    lines = [pad + "{"]
    for k, v in comp.items():
        lines.append(f'{inner}"{k}": {format_value(v)},')
    lines.append(pad + "},")
    return "\n".join(lines)


def components_to_python(components, spaces, interior_walls):
    n_spaces = sum(1 for c in components if c["type"] == "Space")
    n_int    = sum(1 for c in components
                   if c["type"] == "Building_surface"
                   and c.get("surface_type") == "INTERIOR")
    n_ext    = sum(1 for c in components
                   if c["type"] == "Building_surface"
                   and c.get("surface_type") == "EXTERIOR")
    n_ug     = sum(1 for c in components
                   if c["type"] == "Building_surface"
                   and c.get("surface_type") == "UNDERGROUND")

    header = [
        "# Componentes generados automáticamente desde DXF",
        f"# Espacios: {n_spaces}",
        f"# Building_surface EXTERIOR:    {n_ext}",
        f"# Building_surface INTERIOR:    {n_int}  ← paredes medianeras detectadas",
        f"# Building_surface UNDERGROUND: {n_ug}  ← soleras",
        "#",
        "# COMPLETAR antes de usar:",
        "#   spaces_type   → Space_type de cada zona",
        "#   construction  → construcción real de cada superficie",
        "#   ground_material → material de terreno en soleras UNDERGROUND",
        "",
        "dxf_components = [",
    ]
    body = [format_component(c) for c in components]
    footer = ["]"]
    return "\n".join(header + body + footer)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="DXF → componentes OpenSimula con detección de paredes interiores"
    )
    parser.add_argument("dxf",           help="Ruta al archivo .dxf")
    parser.add_argument("--height",      type=float, default=3.0,
                        help="Altura libre de planta en m (defecto: 3.0)")
    parser.add_argument("--z_floor",     type=float, default=0.0,
                        help="Cota Z del suelo en m (defecto: 0.0)")
    parser.add_argument("--building",    default="edificio",
                        help="Nombre del componente Building (defecto: 'edificio')")
    parser.add_argument("--layer",       nargs="+",
                        help="Capas a extraer (defecto: todas)")
    parser.add_argument("--output",
                        help="Archivo .py de salida (defecto: stdout)")
    parser.add_argument("--list-layers", action="store_true",
                        help="Solo listar capas y salir")
    args = parser.parse_args()

    if args.list_layers:
        doc = ezdxf.readfile(args.dxf)
        print("Capas disponibles:")
        for layer in doc.layers:
            print(f"  {layer.dxf.name}")
        return

    spaces = read_spaces(args.dxf, args.layer)
    interior_walls = detect_interior_walls(spaces)
    print_summary(spaces, interior_walls)

    components = extract_components(
        args.dxf,
        height=args.height,
        z_floor=args.z_floor,
        building=args.building,
        layers=args.layer,
    )
    source = components_to_python(components, spaces, interior_walls)

    if args.output:
        Path(args.output).write_text(source, encoding="utf-8")
        print(f"Escrito en: {args.output}")
    else:
        print(source)


if __name__ == "__main__":
    main()
