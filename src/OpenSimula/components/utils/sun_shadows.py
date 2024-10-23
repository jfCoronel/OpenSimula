import numpy as np
import math
import pyvista
from shapely.geometry import Polygon
from triangle import triangulate


class Building_3D():
    def __init__(self):
        self.polygons = []
        self.pol_types = []
        self.polygon_surface = []  # Reference to the surface object
        self.sunny_list = []
        self.sunny_surface = []  # Reference to the sunny surface object
        self.shadow_list = []

    def add_polygon(self, polygon, pol_type, surface_reference=None):
        self.polygons.append(polygon)
        self.pol_types.append(pol_type)
        self.polygon_surface.append(surface_reference)
        if pol_type == "Exterior_surface" or pol_type == "Opening":
            self.sunny_list.append(polygon)
            self.sunny_surface.append(surface_reference)
        if pol_type == "Shadow_surface" or pol_type == "Exterior_surface":
            if polygon.has_holes():
                pol_without_holes = Polygon_3D(
                    polygon.origin, polygon.azimuth, polygon.altitude, polygon.polygon2D, [])
                self.shadow_list.append(pol_without_holes)
            else:
                self.shadow_list.append(polygon)

    def show(self, hide=[], opacity=1):
        draw = Draw_3D()
        if not isinstance(opacity, list):
            opacity = [opacity] * len(self.polygons)
        for polygon, pol_type, opa in zip(self.polygons, self.pol_types, opacity):
            if pol_type == "Opening" and "Opening" not in hide:
                draw.add_polygon(polygon, "blue", opa*0.6)
            elif pol_type == "Virtual_surface" and "Virtual_surface" not in hide:
                draw.add_polygon(polygon, "red", opa*0.4)
            elif pol_type == "Interior_surface" and "Interior_surface" not in hide:
                draw.add_polygon(polygon, "green", opa)
            elif pol_type == "Exterior_surface" and "Exterior_surface" not in hide:
                draw.add_polygon(polygon, "white", opa)
            elif pol_type == "Underground_surface" and "Underground_surface" not in hide:
                draw.add_polygon(polygon, "brown", opa)
            elif pol_type == "Shadow_surface" and "Shadow_surface" not in hide:
                draw.add_polygon(polygon, "cyan", opa)
        draw.show()

    def show_shadows(self, sun_position):
        shadow_polygons = []
        for sunny_polygon in self.sunny_list:
            shadow_polygons.append(sunny_polygon.get_shadow_polygon3D(
                self.shadow_list, sun_position))
        shadow_polygons = sum(shadow_polygons, [])

        draw = Draw_3D()
        for polygon, pol_type in zip(self.polygons, self.pol_types):
            if pol_type == "Opening":
                draw.add_polygon(polygon, "blue", 0.6)
            elif pol_type == "Exterior_surface":
                draw.add_polygon(polygon, "white")
            elif pol_type == "Underground_surface":
                draw.add_polygon(polygon, "brown")
            elif pol_type == "Shadow_surface":
                draw.add_polygon(polygon, "cyan")
        for polygon in shadow_polygons:
            draw.add_polygon(polygon.get_advanced_polygon(), "gray")
        draw.show()

    def get_sunny_fractions(self, sun_position):
        area_fraction = []
        for sunny_polygon in self.sunny_list:
            sunny_fraction_polygon = sunny_polygon.get_sunny_shapely_polygon(
                self.shadow_list, sun_position)
            if sunny_fraction_polygon == None:
                area_fraction.append(0.0)
            else:
                area_fraction.append(
                    sunny_fraction_polygon.area/sunny_polygon.area)
        return np.array(area_fraction)


class Polygon_3D():
    def __init__(self, origin, azimuth, altitude, polygon2D, holes2D=[]):
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
        self.polygon3D = self.convert_2D_to_3D(self.polygon2D)
        self.holes2D = holes2D
        self.holes3D = []
        for hole in self.holes2D:
            self.holes3D.append(self.convert_2D_to_3D(hole))
        self.shapely_polygon = Polygon(self.polygon2D, self.holes2D)
        self.area = self.shapely_polygon.area
        self.equation_d = np.sum(self.normal_vector*self.origin)

    def has_holes(self):
        if (len(self.holes2D) > 0):
            return True
        else:
            return False

    def is_coplanar(self, polygon):
        if np.allclose(self.normal_vector, polygon.normal_vector):  # same normal verctor
            if np.isclose(np.sum(self.normal_vector*polygon.origin), self.equation_d):  # in the plane
                return True
            else:
                return False
        else:
            return False

    def get_advanced_polygon(self):
        advanced_origin = self.origin + self.normal_vector*1e-4
        advanced = Polygon_3D(advanced_origin, self.azimuth,
                              self.altitude, self.polygon2D, self.holes2D)
        return advanced

    def convert_2D_to_3D(self, pol_2D):
        pol_3D = []
        for vertex in pol_2D:
            v_loc = (self.origin[0] + vertex[0] * math.cos(self.azimuth_rad)
                     - vertex[1] * math.sin(self.altitude_rad) *
                     math.sin(self.azimuth_rad),
                     self.origin[1] + vertex[0] * math.sin(self.azimuth_rad)
                     + vertex[1] * math.sin(self.altitude_rad) *
                     math.cos(self.azimuth_rad),
                     self.origin[2] + vertex[1] * math.cos(self.altitude_rad))
            pol_3D.append(v_loc)
        return pol_3D

    def is_facing_sun(self, sun_position):
        escalar_p = np.sum(self.normal_vector*sun_position)
        if escalar_p >= 1e-10:
            return True
        else:
            return False

    def get_pyvista_mesh(self):
        if self.has_holes():
            (points, faces) = self._triangulate_()
            return pyvista.PolyData(points, faces=faces)
        else:
            faces = [len(self.polygon3D), *range(0, len(self.polygon3D))]
            return pyvista.PolyData(np.array(self.polygon3D), faces)

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
        d = triangulate(
            dict(vertices=verts, segments=edges, holes=holes), opts='p')

        # Convert back to pyvista
        v, f = d['vertices'], d['triangles']
        nv, nf = len(v), len(f)
        points = np.concatenate([v, np.zeros((nv, 1))], axis=1)
        # Creo que lo tengo que hacer en 2D y luego pasarlo a 3D
        faces = np.concatenate([np.full((nf, 1), 3), f], axis=1).reshape(-1)
        return (self.convert_2D_to_3D(points), faces)

    def get_pyvista_polygon_border(self):
        return np.vstack([np.array(self.polygon3D), self.polygon3D[0]])

    def get_pyvista_hole_border(self, i):
        return np.vstack([np.array(self.holes3D[i]), self.holes3D[i][0]])

    def get_sunny_shapely_polygon(self, shadow_polygons_list, sun_position):
        if not self.is_facing_sun(sun_position):
            return None
        else:
            # Calculate projected shadows
            shadows_2D = []
            for shadow_polygon in shadow_polygons_list:
                if shadow_polygon.is_facing_sun(sun_position):
                    shadows_2D.append(self._calculate_shapely_2D_projected_(
                        shadow_polygon, sun_position))
            # Calculate sunny polygon
            sunny_polygon = self.shapely_polygon
            for shadow_polygon in shadows_2D:
                if shadow_polygon != None:
                    sunny_polygon = sunny_polygon.difference(shadow_polygon)
            if sunny_polygon.is_empty:
                sunny_polygon = None
            return sunny_polygon

    def get_sunny_polygon3D(self, shadow_polygons_list, sun_position):
        return self._shapely_multipolygon_to_polygons_3D_(self.get_sunny_shapely_polygon(shadow_polygons_list, sun_position))

    def get_shadow_shapely_polygon(self, shadow_polygons_list, sun_position):
        sunny_polygon = self.get_sunny_shapely_polygon(
            shadow_polygons_list, sun_position)
        if sunny_polygon == None:
            return self.shapely_polygon
        else:
            shadow_polygon = self.shapely_polygon.difference(sunny_polygon)
            if shadow_polygon.is_empty:
                return None
            else:
                return shadow_polygon

    def get_shadow_polygon3D(self, shadow_polygons_list, sun_position):
        return self._shapely_multipolygon_to_polygons_3D_(self.get_shadow_shapely_polygon(shadow_polygons_list, sun_position))

    def _calculate_shapely_2D_projected_(self, polygon_to_project, sun_position):
        projected_polygon = []
        n_points = 0
        k_total = 0
        for point in polygon_to_project.polygon3D:
            k = (np.sum(self.normal_vector * point)-self.equation_d) / \
                (np.sum(self.normal_vector * sun_position))
            projected_point_3D = point - k * sun_position
            vector = projected_point_3D - self.origin
            projected_point_2D = np.array(
                [np.sum(self.x_axis*vector), np.sum(self.y_axis*vector)])
            projected_polygon.append(projected_point_2D)
            if (k > -1e-6):  # Por delante o en el plano
                n_points += 1
            if (k > 0.1):  # 10 cm
                k_total += k
        # TODO: que ocurre cuando tengo planos cortantes ...
        if n_points > 2 and k_total > 0.1:
            return Polygon(projected_polygon)
        else:
            return None

    # Para dibujarlos en 3D
    def _shapely_multipolygon_to_polygons_3D_(self, shapely_polygon):
        polygon_list = []
        if shapely_polygon != None:
            if shapely_polygon.geom_type == 'MultiPolygon':
                polygons = list(shapely_polygon.geoms)
                for pol in polygons:
                    polygon_list.append(self._shapely_to_polygon_3D_(pol))
            elif shapely_polygon.geom_type == 'Polygon':
                polygon_list.append(
                    self._shapely_to_polygon_3D_(shapely_polygon))
        return polygon_list

    def _shapely_to_polygon_3D_(self, shapely_pol):
        exterior_pol = np.asarray(shapely_pol.exterior.coords)
        holes = [(np.asarray(ring.coords)) for ring in shapely_pol.interiors]
        return Polygon_3D(self.origin, self.azimuth, self.altitude, exterior_pol, holes)


class Draw_3D():
    def __init__(self, default="white"):
        self.default_color = default
        self.plot = pyvista.Plotter()
        self.plot.add_axes_at_origin()

    def add_polygon(self, polygon, color=None, opacity=1):
        if color == None:
            color = self.default_color
        if polygon != None:
            self.plot.add_mesh(polygon.get_pyvista_mesh().triangulate(
            ), show_edges=False, color=color, opacity=opacity)
            self.plot.add_lines(polygon.get_pyvista_polygon_border(
            ), color="black", width=5, connected=True)
            if (polygon.has_holes()):
                for i in range(len(polygon.holes2D)):
                    self.plot.add_lines(polygon.get_pyvista_hole_border(
                        i), color="black", width=5, connected=True)

    def add_polygons(self, polygons_list, color=None, opacity=1):
        for polygon in polygons_list:
            if color == None:
                self.add_polygon(polygon, self.default_color, opacity=opacity)
            else:
                self.add_polygon(polygon, color, opacity=opacity)

    def show(self):
        self.plot.show(jupyter_backend="client")


# class Plane_3D():
#     def __init__(self,polygon3D):
#         self.normal_vector = polygon3D.normal_vector
#         self.origin = polygon3D.origin
#         self.equation_d = np.sum(self.normal_vector*self.origin)
#         self.x_axis = (math.cos(polygon3D.azimuth_rad),
#                        math.sin(polygon3D.azimuth_rad),
#                        0)
#         self.y_axis = np.cross(self.normal_vector,self.x_axis)
#         self.interior_pol = [polygon3D]

#     def add_polygon(self,polygon3D):
#         self.interior_pol.append(polygon3D)

#     def is_facing_sun(self, sun_position):
#         return self.interior_pol[0].is_facing_sun(sun_position)

#     def is_coplanar(self, polygon):
#         if np.allclose(self.normal_vector,polygon.normal_vector):
#             if  np.isclose(np.sum(self.normal_vector*polygon.origin),self.equation_d):
#                 return True
#             else:
#                 return False
#         else:
#             return False

#     def get_sunny_shapely_polygon(self, shadow_polygons_list, sun_position):
#         if not self.is_facing_sun(sun_position):
#             empty = []
#             for polygon in self.interior_pol:
#                 empty.append(None)
#             return empty
#         else:
#             # Calculate projected shadows
#             shadows_2D = []
#             for shadow_polygon in shadow_polygons_list:
#                 if shadow_polygon.is_facing_sun(sun_position):
#                         shadows_2D.append(self._calculate_shapely_2D_projected_(shadow_polygon,sun_position))
#             # Calculate sunny polygons
#             sunny = []
#             for polygon in self.interior_pol:
#                 sunny_polygon = polygon.shapely_polygon
#                 for shadow_polygon in shadows_2D:
#                     if shadow_polygon != None:
#                         sunny_polygon = sunny_polygon.difference(shadow_polygon)
#                 if sunny_polygon.is_empty:
#                     sunny.append(None)
#                 else:
#                     sunny.append(sunny_polygon)
#             return sunny

#     def get_sunny_polygon3D(self, shadow_polygons_list, sun_position):
#         return self._shapely_list_to_polygons_3D_(self.get_sunny_shapely_polygon(shadow_polygons_list,sun_position))

#     def get_shadow_shapely_polygon(self, shadow_polygons_list, sun_position):
#         sunny = self.get_sunny_shapely_polygon(shadow_polygons_list,sun_position)
#         shadow = []
#         for i in range(len(self.interior_pol)):
#             if sunny[i] == None:
#                 shadow_pol = self.interior_pol[i].shapely_polygon
#             else:
#                 shadow_pol = self.interior_pol[i].shapely_polygon.difference(sunny[i])
#             if shadow_pol.is_empty:
#                 shadow.append(None)
#             else:
#                 shadow.append(shadow_pol)
#         return shadow

#     def get_shadow_polygon3D(self, shadow_polygons_list, sun_position):
#         return self._shapely_list_to_polygons_3D_(self.get_shadow_shapely_polygon(shadow_polygons_list,sun_position))

#     def _calculate_shapely_2D_projected_(self, polygon_to_project, sun_position):
#         projected_polygon = []
#         k_vertex = []
#         for point in polygon_to_project.polygon3D:
#             k = (np.sum(self.normal_vector * point)-self.equation_d)/(np.sum(self.normal_vector * sun_position))
#             if k >= -1e-6:
#                 projected_point_3D = point - k * sun_position
#                 vector = projected_point_3D - self.origin
#                 projected_point_2D = np.array([np.sum(self.x_axis*vector),np.sum(self.y_axis*vector)])
#                 projected_polygon.append(projected_point_2D)
#                 k_vertex.append(k)
#         if sum(k_vertex)>1e-4: # TODO: que ocurre cuando tengo planos cortantes
#             return Polygon(projected_polygon)
#         else:
#             return None

#     def _shapely_list_to_polygons_3D_(self,shapely_2D_list): # Para dibujarlos en 3D
#         polygon_list=[]
#         for shape_polygon in shapely_2D_list:
#             if shape_polygon != None:
#                 if shape_polygon.geom_type == 'MultiPolygon':
#                     polygons = list(shape_polygon.geoms)
#                     for pol in polygons:
#                         polygon_list.append(self._shapely_to_polygon_3D_(pol))
#                 elif shape_polygon.geom_type == 'Polygon':
#                     polygon_list.append(self._shapely_to_polygon_3D_(shape_polygon))
#         return polygon_list

#     def _shapely_to_polygon_3D_(self,shapely_pol):
#         exterior_pol = np.asarray(shapely_pol.exterior.coords)
#         holes = [(np.asarray(ring.coords)) for ring in shapely_pol.interiors]
#         return Polygon_3D(self.origin,self.interior_pol[0].azimuth,self.interior_pol[0].altitude,exterior_pol,holes)
