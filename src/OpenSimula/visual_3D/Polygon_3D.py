import math
import numpy as np
from shapely.geometry import Polygon, MultiPoint
from shapely.ops import triangulate as shapely_triangulate, unary_union
import vedo

class Polygon_3D():
    def __init__(self, name, origin, azimuth, altitude, polygon2D, holes2D=[], color="white", opacity=1.0, visible=True,shading=True,calculate_shadows=True):
        self.name = name
        self.origin = np.array(origin)
        self.azimuth = azimuth
        self.altitude = altitude
        self.polygon2D = polygon2D
        self.azimuth_rad = math.radians(self.azimuth)
        self.altitude_rad = math.radians(self.altitude)
        self.normal_vector = np.array((math.cos(self.altitude_rad)*math.sin(self.azimuth_rad),
                                       -math.cos(self.altitude_rad) *
                                       math.cos(self.azimuth_rad),
                                       math.sin(self.altitude_rad)))
        self.x_axis = np.array((math.cos(self.azimuth_rad),
                                math.sin(self.azimuth_rad),
                                0))
        self.y_axis = np.cross(self.normal_vector, self.x_axis)
        self.polygon3D = self._convert_2D_to_3D_(self.polygon2D)
        self.holes2D = holes2D
        self.holes3D = []
        for hole in self.holes2D:
            self.holes3D.append(self._convert_2D_to_3D_(hole))
        self.shapely_polygon = self._build_shapely_polygon_(
            self.polygon2D, self.holes2D)
        self.area = self.shapely_polygon.area
        # self.centroid2D = self.shapely_polygon.centroid.coords[0]
        # self.centroid3D = self._convert_2D_to_3D_([self.centroid2D])[0]
        self.equation_d = np.sum(self.normal_vector*self.origin)
        self.color = color
        self.opacity = opacity
        self.visible = visible
        self.shading = shading
        self.calculate_shadows = calculate_shadows
        self._prepare_shadow_data_()

    @staticmethod
    def _build_shapely_polygon_(exterior, holes):
        """Build the polygon of an outline with its holes.

        Passing the holes to Polygon() fails when a hole touches the outline
        (an opening flush with a surface edge, usual in imported geometry): the
        shell gets pinched by its own hole and the result is an invalid polygon.
        Subtracting the holes instead gives the equivalent valid single ring.

        The subtraction is only used for those cases: when the direct form is
        already valid it is kept as is, because the boolean operation re-nodes
        the geometry and would perturb results that are correct today.
        """
        if not holes:
            return Polygon(exterior)
        polygon = Polygon(exterior, holes)
        if polygon.is_valid:
            return polygon
        return Polygon(exterior).difference(
            unary_union([Polygon(hole) for hole in holes])
        )

    def _prepare_shadow_data_(self):
        """Cache the geometry used by the shadow projection as plain floats.

        The projection works on 3-component vectors, where numpy's per-call
        overhead dominates the arithmetic itself. Storing the same data as
        Python floats/tuples makes the inner loops several times faster.
        """
        self._f_normal_ = (float(self.normal_vector[0]),
                           float(self.normal_vector[1]),
                           float(self.normal_vector[2]))
        self._f_origin_ = (float(self.origin[0]), float(self.origin[1]),
                           float(self.origin[2]))
        self._f_x_axis_ = (float(self.x_axis[0]), float(self.x_axis[1]),
                           float(self.x_axis[2]))
        self._f_y_axis_ = (float(self.y_axis[0]), float(self.y_axis[1]),
                           float(self.y_axis[2]))
        self._f_equation_d_ = float(self.equation_d)
        self._f_polygon3D_ = [(float(p[0]), float(p[1]), float(p[2]))
                              for p in self.polygon3D]
        self._f_holes3D_ = [[(float(p[0]), float(p[1]), float(p[2]))
                             for p in hole] for hole in self.holes3D]
        # Bounding sphere, to discard casting polygons lying entirely behind
        # this polygon plane, before projecting any of their vertices.
        points = self._f_polygon3D_
        if points:
            n_points = len(points)
            c_x = sum(p[0] for p in points) / n_points
            c_y = sum(p[1] for p in points) / n_points
            c_z = sum(p[2] for p in points) / n_points
            self._f_center_ = (c_x, c_y, c_z)
            self._f_radius_ = max(
                math.sqrt((p[0] - c_x) ** 2 + (p[1] - c_y) ** 2 + (p[2] - c_z) ** 2)
                for p in points
            )
        else:
            self._f_center_ = (0.0, 0.0, 0.0)
            self._f_radius_ = 0.0
        # Set of ids of the polygons coplanar with this one. Coplanarity does
        # not depend on the sun position, so Environment_3D fills it once.
        self._coplanar_ids_ = frozenset()

    def has_holes(self):
        if (len(self.holes2D) > 0):
            return True
        else:
            return False

    def are_coplanar(self, polygon_3D):
        if np.allclose(self.normal_vector, polygon_3D.normal_vector):  # same normal verctor
            if np.isclose(np.sum(self.normal_vector*polygon_3D.origin), self.equation_d):  # in the plane
                return True
            else:
                return False
        else:
            return False
    
    def _convert_2D_to_3D_(self, pol_2D):
        pol_3D = []
        for vertex in pol_2D:
            v_loc = np.array([self.origin[0] + vertex[0] * math.cos(self.azimuth_rad)
                     - vertex[1] * math.sin(self.altitude_rad) *
                     math.sin(self.azimuth_rad),
                     self.origin[1] + vertex[0] * math.sin(self.azimuth_rad)
                     + vertex[1] * math.sin(self.altitude_rad) *
                     math.cos(self.azimuth_rad),
                     self.origin[2] + vertex[1] * math.cos(self.altitude_rad)])
            pol_3D.append(v_loc)
        return pol_3D
        

    # Functions for vedo
    def get_vedo_mesh(self):
        (points, faces) = self._triangulate_()
        mesh = vedo.Mesh([points, faces])
        mesh.c(self.color).alpha(self.opacity)
        return mesh

    def _triangulate_(self):
        all_verts = list(self.polygon2D)
        for hole in self.holes2D:
            all_verts.extend(hole)

        tris = [t for t in shapely_triangulate(MultiPoint(all_verts))
                if self.shapely_polygon.contains(t.centroid)]

        vert_map = {}
        verts = []
        faces = []
        for tri in tris:
            face = []
            for c in list(tri.exterior.coords)[:-1]:
                key = (round(c[0], 10), round(c[1], 10))
                if key not in vert_map:
                    vert_map[key] = len(verts)
                    verts.append(c)
                face.append(vert_map[key])
            faces.append(face)

        return (self._convert_2D_to_3D_(np.array(verts)), np.array(faces))

    def _are_vertices_counterclockwise_(self,puntos):
        # Se suma el primer punto al final para cerrar el polígono.
        if puntos[-1][0] != puntos[0][0] or puntos[-1][1] != puntos[0][1]:
            puntos_cerrados = np.vstack([puntos, puntos[0]])
        else:
            puntos_cerrados = puntos
        x = puntos_cerrados[:, 0]
        y = puntos_cerrados[:, 1]
        # La suma de los productos cruzados
        suma_productos_cruzados = np.sum(x[:-1] * y[1:] - x[1:] * y[:-1])
        return suma_productos_cruzados > 0

    # Shadow calculations
    def is_facing_sun(self, sun_position):
        n_x, n_y, n_z = self._f_normal_
        escalar_p = (n_x * sun_position[0] + n_y * sun_position[1]
                     + n_z * sun_position[2])
        if escalar_p >= 1e-10:
            return True
        else:
            return False

    def _get_sunny_shadow_shapely_polygon_(self, environment_3D, sun_position):
        sun_x = float(sun_position[0])
        sun_y = float(sun_position[1])
        sun_z = float(sun_position[2])
        n_x, n_y, n_z = self._f_normal_
        # Cosine between the surface normal and the sun. It is the denominator
        # of every point projection onto this plane, so it is computed once.
        cos_sun = n_x * sun_x + n_y * sun_y + n_z * sun_z
        if cos_sun < 1e-10:  # Not facing the sun
            return None, self.shapely_polygon

        coplanar_ids = self._coplanar_ids_
        equation_d = self._f_equation_d_
        sunny_polygon = self.shapely_polygon
        for shadow_polygon in environment_3D.pol_3D:
            if shadow_polygon is self or not shadow_polygon.shading:
                continue
            if id(shadow_polygon) in coplanar_ids:
                continue
            s_x, s_y, s_z = shadow_polygon._f_normal_
            if s_x * sun_x + s_y * sun_y + s_z * sun_z < 1e-10:
                continue  # The casting polygon is not facing the sun
            # Its bounding sphere is fully behind this plane: every vertex
            # would be dropped by the projection, so it casts nothing here.
            c_x, c_y, c_z = shadow_polygon._f_center_
            if (n_x * c_x + n_y * c_y + n_z * c_z - equation_d
                    + shadow_polygon._f_radius_) <= -1e-6:
                continue
            projected = self._calculate_shapely_projected_polygon_(
                shadow_polygon, (sun_x, sun_y, sun_z), cos_sun
            )
            if projected is not None:
                sunny_polygon = sunny_polygon.difference(projected)
                if sunny_polygon.is_empty:  # Fully shaded, nothing left to cut
                    return None, self.shapely_polygon

        shadow_polygon = self.shapely_polygon.difference(sunny_polygon)
        if shadow_polygon.is_empty:
            shadow_polygon = None
        return sunny_polygon, shadow_polygon

    def _calculate_shapely_projected_polygon_(self, polygon_to_project, sun_position, cos_sun=None):
        if cos_sun is None:
            n_x, n_y, n_z = self._f_normal_
            cos_sun = (n_x * sun_position[0] + n_y * sun_position[1]
                       + n_z * sun_position[2])
        exterior_points = self._get_projected_points_(
            polygon_to_project._f_polygon3D_, sun_position, cos_sun
        )
        if exterior_points is None:
            return None
        if polygon_to_project._f_holes3D_:
            holes = []
            for hole in polygon_to_project._f_holes3D_:
                hole_points = self._get_projected_points_(hole, sun_position, cos_sun)
                if hole_points is not None:
                    holes.append(hole_points)
            # The projection is affine, so a hole touching the outline still
            # touches it once projected: same invalid shell-with-hole as the
            # surface it comes from.
            return self._build_shapely_polygon_(exterior_points, holes)
        return Polygon(exterior_points)

    def _get_projected_points_(self, points_3D, sun_position, cos_sun):
        """Project a 3D point ring onto this polygon plane, in its 2D axes.

        Points behind the plane are dropped, and the edge crossing the plane is
        cut at the intersection, so the projected outline stays closed.
        """
        sun_x, sun_y, sun_z = sun_position
        n_x, n_y, n_z = self._f_normal_
        eq_d = self._f_equation_d_
        o_x, o_y, o_z = self._f_origin_
        x_x, x_y, x_z = self._f_x_axis_
        y_x, y_y, y_z = self._f_y_axis_

        def project(p_x, p_y, p_z, dist):
            k = dist / cos_sun
            if k <= -1e-6:  # Behind the plane
                return None
            v_x = p_x - k * sun_x - o_x
            v_y = p_y - k * sun_y - o_y
            v_z = p_z - k * sun_z - o_z
            return (x_x * v_x + x_y * v_y + x_z * v_z,
                    y_x * v_x + y_y * v_y + y_z * v_z)

        projected_points = []
        point_0 = points_3D[-1]
        d_0 = n_x * point_0[0] + n_y * point_0[1] + n_z * point_0[2] - eq_d
        projected_point_0 = project(point_0[0], point_0[1], point_0[2], d_0)
        for point_1 in points_3D:
            d_1 = n_x * point_1[0] + n_y * point_1[1] + n_z * point_1[2] - eq_d
            projected_point_1 = project(point_1[0], point_1[1], point_1[2], d_1)
            if projected_point_1 is not None and projected_point_0 is not None:
                projected_points.append(projected_point_1)
            elif projected_point_1 is not None or projected_point_0 is not None:
                if d_0 * d_1 < -1e-10:  # The edge crosses the plane
                    t = d_0 / (d_0 - d_1)
                    i_x = point_0[0] + t * (point_1[0] - point_0[0])
                    i_y = point_0[1] + t * (point_1[1] - point_0[1])
                    i_z = point_0[2] + t * (point_1[2] - point_0[2])
                    d_i = n_x * i_x + n_y * i_y + n_z * i_z - eq_d
                    projected_intersection = project(i_x, i_y, i_z, d_i)
                    if projected_intersection is not None:
                        projected_points.append(projected_intersection)
                if projected_point_1 is not None:
                    projected_points.append(projected_point_1)
            point_0 = point_1
            d_0 = d_1
            projected_point_0 = projected_point_1
        if len(projected_points) < 3:
            return None
        return projected_points

    def get_sunny_shadow_polygon3D(self, environment_3D, sun_position):
        sunny_polygons, shadow_polygons = self._get_sunny_shadow_shapely_polygon_(environment_3D, sun_position)
        sunny_polygons_3D = self._shapely_multipolygon_to_polygons_3D_(sunny_polygons,"sunny")
        shadow_polygons_3D = self._shapely_multipolygon_to_polygons_3D_(shadow_polygons,"shadow")
        return sunny_polygons_3D, shadow_polygons_3D
    
    # Para dibujarlos en 3D
    # Below this area [m2], a polygon resulting from a shapely difference()
    # is floating-point noise (near-collinear vertices), not real geometry.
    # Such slivers triangulate to zero faces and would crash the 3D renderer.
    _MIN_POLYGON_AREA_ = 1e-6

    def _shapely_multipolygon_to_polygons_3D_(self, shapely_polygon, type="sunny"):
        polygon_list = []
        if shapely_polygon is not None:
            if shapely_polygon.geom_type == 'MultiPolygon':
                for pol in shapely_polygon.geoms:
                    if pol.area > self._MIN_POLYGON_AREA_:
                        polygon_list.append(self._shapely_to_polygon_3D_(pol,type))
            elif shapely_polygon.geom_type == 'Polygon':
                if shapely_polygon.area > self._MIN_POLYGON_AREA_:
                    polygon_list.append(
                        self._shapely_to_polygon_3D_(shapely_polygon,type))
            elif shapely_polygon.geom_type == 'GeometryCollection':
                # difference() between near-tangent/coplanar polygons can return a
                # GeometryCollection mixing degenerate LineStrings/Points/slivers with
                # the actual resulting Polygon(s); keep only the real polygonal parts.
                for geom in shapely_polygon.geoms:
                    if geom.geom_type == 'Polygon' and geom.area > self._MIN_POLYGON_AREA_:
                        polygon_list.append(self._shapely_to_polygon_3D_(geom, type))
                    elif geom.geom_type == 'MultiPolygon':
                        for pol in geom.geoms:
                            if pol.area > self._MIN_POLYGON_AREA_:
                                polygon_list.append(self._shapely_to_polygon_3D_(pol, type))
        return polygon_list

    def _shapely_to_polygon_3D_(self, shapely_pol, type="sunny"):
        exterior_pol = np.asarray(shapely_pol.exterior.coords)
        if not self._are_vertices_counterclockwise_(exterior_pol):
            exterior_pol = exterior_pol[::-1]
        if exterior_pol[-1][0] == exterior_pol[0][0] and exterior_pol[-1][1] == exterior_pol[0][1]:
            exterior_pol = exterior_pol[:-1]
        holes = []
        for interior in shapely_pol.interiors:
            interior_pol = np.asarray(interior.coords)
            if not self._are_vertices_counterclockwise_(interior_pol):
                interior_pol = interior_pol[::-1]
            if interior_pol[-1][0] == interior_pol[0][0] and interior_pol[-1][1] == interior_pol[0][1]:
                interior_pol = interior_pol[:-1]
            holes.append(interior_pol)
        if type=="sunny":
            pol_3D = Polygon_3D(self.name+"_sunny",self.origin, self.azimuth, self.altitude, exterior_pol, holes,color=self.color,opacity=self.opacity)
        else:
            pol_3D = Polygon_3D(self.name+"_shadow",self.origin, self.azimuth, self.altitude, exterior_pol, holes, color="gray3")
        return pol_3D
    
    def get_angle_with_normal(self, sol_azimuth, sol_altitude):
        azi_r = math.radians(sol_azimuth)
        alt_r = math.radians(sol_altitude)
        sol_vector = np.array([math.cos(alt_r)*math.cos(azi_r-math.pi/2),
                              math.cos(alt_r)*math.sin(azi_r-math.pi/2), math.sin(alt_r)])
        return np.arccos(np.clip(np.dot(self.normal_vector, sol_vector), -1.0, 1.0))

