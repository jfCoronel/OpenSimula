import math
import numpy as np
from shapely.geometry import Polygon
import vedo
from triangle import triangulate

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
        self.shapely_polygon = Polygon(self.polygon2D, self.holes2D)
        self.area = self.shapely_polygon.area
        # self.centroid2D = self.shapely_polygon.centroid.coords[0]
        # self.centroid3D = self._convert_2D_to_3D_([self.centroid2D])[0]
        self.equation_d = np.sum(self.normal_vector*self.origin)
        self.color = color
        self.opacity = opacity
        self.visible = visible
        self.shading = shading
        self.calculate_shadows = calculate_shadows

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
        def edge_idxs(nv):
            i = np.append(np.arange(nv), 0)
            return np.stack([i[:-1], i[1:]], axis=1)

        nv = 0
        verts, edges = [], []
        for loop in (self.polygon2D, *self.holes2D):
            verts.append(loop)
            edges.append(nv + edge_idxs(len(loop)))
            nv += len(loop)

        verts, edges = np.concatenate(verts), np.concatenate(edges)
        # Triangulate needs to know a single interior point for each hole
        holes = np.array([np.mean(h, axis=0) for h in self.holes2D])
        # Because triangulate is a wrapper around a C library the syntax is a little weird, 'p' here means planar straight line graph
        if self.has_holes():
            d = triangulate(dict(vertices=verts, segments=edges, holes=holes), opts='p')
        else:
            d = triangulate(dict(vertices=verts, segments=edges), opts='p')
        # Convert back 
        v, f = d['vertices'], d['triangles']
        nv, nf = len(v), len(f)
        points = np.concatenate([v, np.zeros((nv, 1))], axis=1)
        # Creo que lo tengo que hacer en 2D y luego pasarlo a 3D
        #faces = np.concatenate([np.full((nf, 1), 3), f], axis=1).reshape(-1)
        return (self._convert_2D_to_3D_(points), f)

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
        escalar_p = np.sum(self.normal_vector*sun_position)
        if escalar_p >= 1e-10:
            return True
        else:
            return False

    def _get_sunny_shadow_shapely_polygon_(self, environment_3D, sun_position):
        if not self.is_facing_sun(sun_position):
            sunny_polygon = None
            shadow_polygon = self.shapely_polygon
        else:
            # Calculate projected shadows
            shadows_2D = []
            for shadow_polygon in environment_3D.pol_3D:
                if shadow_polygon != self and shadow_polygon.shading == True:
                    if shadow_polygon.is_facing_sun(sun_position):
                        if not self.are_coplanar(shadow_polygon):
                            shadows_2D.append(self._calculate_shapely_projected_polygon_(shadow_polygon, sun_position))

            # Calculate sunny polygon
            sunny_polygon = self.shapely_polygon
            for shadow_polygon in shadows_2D:
                if shadow_polygon != None:
                    sunny_polygon = sunny_polygon.difference(shadow_polygon)
            if sunny_polygon.is_empty:
                sunny_polygon = None
                shadow_polygon = self.shapely_polygon
            else:
                shadow_polygon = self.shapely_polygon.difference(sunny_polygon)
                if shadow_polygon.is_empty:
                    shadow_polygon = None
        return sunny_polygon, shadow_polygon
    
    def _calculate_shapely_projected_polygon_(self, polygon_to_project, sun_position):
        exterior_points = self._get_projected_points_(polygon_to_project, sun_position)
        if exterior_points != None:
            if polygon_to_project.has_holes():
                holes = []
                for hole in polygon_to_project.holes2D:
                    hole_points = self._get_projected_points_(
                        Polygon_3D("holes", polygon_to_project.origin, polygon_to_project.azimuth, polygon_to_project.altitude, hole), sun_position)
                    if hole_points != None:
                        holes.append(hole_points)
                return Polygon(exterior_points, holes)
            else:
                return Polygon(exterior_points)
        else:
            return None

    def _get_projected_points_(self,polygon_to_project, sun_position):
        projected_points = []
        point_0 = polygon_to_project.polygon3D[-1]
        projected_point_0 = self._get_projected_point_(point_0, sun_position)
        for point_1 in polygon_to_project.polygon3D:
            projected_point_1 = self._get_projected_point_(point_1, sun_position)
            if len(projected_point_1) > 0 and len(projected_point_0) > 0:
                projected_points.append(projected_point_1)
            elif (len(projected_point_1) > 0 and len(projected_point_0)==0) or (len(projected_point_1) == 0 and len(projected_point_0) > 0):
                intersection_point = self._get_intersection_with_plane_(point_0, point_1)
                projected_intersection_point = self._get_projected_point_(intersection_point, sun_position)
                projected_points.append(projected_intersection_point)
            point_0 = np.array(point_1)
            if len(projected_point_1) > 0:
                projected_point_0 = np.array(projected_point_1)
            else:
                projected_point_0 = np.array([])
        if len(projected_points) < 3:
            return None
        else:
            return projected_points
    
    def _get_projected_point_(self, point, sun_position):
        d = np.sum(self.normal_vector*point)-self.equation_d
        k = d/np.sum(self.normal_vector*sun_position)
        if (k > -1e-6):  # Por delante
            projected_point_3D = point - k*sun_position
            vector = projected_point_3D - self.origin
            projected_point_2D = np.array([np.sum(self.x_axis*vector), np.sum(self.y_axis*vector)])
            return projected_point_2D
        else:
            return np.array([])
        
    def _get_intersection_with_plane_(self, point_0,point_1):
        d0 = np.sum(self.normal_vector*point_0)-self.equation_d
        d1 = np.sum(self.normal_vector*point_1)-self.equation_d
        if (d0*d1 < -1e-10):  # Si están en lados opuestos
            t = d0/(d0-d1)
            intersection_point = point_0 + t*(point_1-point_0)
            return intersection_point
        else:
            return np.array([])

    def get_sunny_shadow_polygon3D(self, environment_3D, sun_position):
        sunny_polygons, shadow_polygons = self._get_sunny_shadow_shapely_polygon_(environment_3D, sun_position)
        sunny_polygons_3D = self._shapely_multipolygon_to_polygons_3D_(sunny_polygons,"sunny")
        shadow_polygons_3D = self._shapely_multipolygon_to_polygons_3D_(shadow_polygons,"shadow")
        return sunny_polygons_3D, shadow_polygons_3D
    
    # Para dibujarlos en 3D
    def _shapely_multipolygon_to_polygons_3D_(self, shapely_polygon, type="sunny"):
        polygon_list = []
        if shapely_polygon != None:
            if shapely_polygon.geom_type == 'MultiPolygon':
                polygons = list(shapely_polygon.geoms)
                for pol in polygons:
                    polygon_list.append(self._shapely_to_polygon_3D_(pol,type))
            elif shapely_polygon.geom_type == 'Polygon':
                polygon_list.append(
                    self._shapely_to_polygon_3D_(shapely_polygon,type))
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

