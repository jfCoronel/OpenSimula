import time
import numpy as np
import math
from scipy.interpolate import RegularGridInterpolator
import matplotlib.pyplot as plt
import vedo as vedo

class Environment_3D:
    def __init__(self):
        self.pol_3D = []
        self.pol_sunny = []
        self.pol_shadows = []
        self.sunny_fraction = []
        self.solar_tables_calculated = False

    def add_polygon_3D(self, polygon_3D):
        self.pol_3D.append(polygon_3D)
        self.sunny_fraction.append(1.0)

    def get_vedo_meshes(self, polygons_type="initial"):
        meshes = []
        if polygons_type == "initial":
            for polygon_3D in self.pol_3D:
                if polygon_3D.visible:
                    mesh = polygon_3D.get_vedo_mesh()
                    mesh.polygon_name = polygon_3D.name
                    meshes.append(mesh)
                    meshes.append(mesh.silhouette("2d").c("black").linewidth(5))
        elif polygons_type == "sunny":
            for polygon_3D in self.pol_sunny:
                mesh = polygon_3D.get_vedo_mesh()
                mesh.polygon_name = polygon_3D.name
                meshes.append(mesh)
                meshes.append(mesh.silhouette("2d").c("black").linewidth(5))
        elif polygons_type == "shadows":
            for polygon_3D in self.pol_shadows:
                mesh = polygon_3D.get_vedo_mesh()
                mesh.polygon_name = polygon_3D.name
                meshes.append(mesh)
                meshes.append(mesh.silhouette("2d").c("black").linewidth(5))
        elif polygons_type == "sunny+shadows":
            for polygon_3D in self.pol_sunny:
                mesh = polygon_3D.get_vedo_mesh()
                mesh.polygon_name = polygon_3D.name
                meshes.append(mesh)
                meshes.append(mesh.silhouette("2d").c("black").linewidth(5))
            for polygon_3D in self.pol_shadows:
                mesh = polygon_3D.get_vedo_mesh()
                mesh.polygon_name = polygon_3D.name
                meshes.append(mesh)
                meshes.append(mesh.silhouette("2d").c("black").linewidth(5))
        elif polygons_type == "Building_shadows":
            for polygon_3D in self.pol_sunny:
                mesh = polygon_3D.get_vedo_mesh()
                mesh.polygon_name = polygon_3D.name
                meshes.append(mesh)
                meshes.append(mesh.silhouette("2d").c("black").linewidth(5))
            for polygon_3D in self.pol_shadows:
                mesh = polygon_3D.get_vedo_mesh()
                mesh.polygon_name = polygon_3D.name
                meshes.append(mesh)
                meshes.append(mesh.silhouette("2d").c("black").linewidth(5))
            for polygon_3D in self.pol_3D:
                if polygon_3D.visible and polygon_3D.calculate_shadows == False:
                    mesh = polygon_3D.get_vedo_mesh()
                    mesh.polygon_name = polygon_3D.name
                    meshes.append(mesh)
                    meshes.append(mesh.silhouette("2d").c("black").linewidth(5))

        return meshes

    def show(self, polygons_type="initial"):
        vedo.settings.default_backend = 'vtk'
        meshes = self.get_vedo_meshes(polygons_type)
        
        text_obj = [None]  # Usamos una lista para que sea mutable en el callback

        def on_left_click(evt):
            if text_obj[0] is not None:
                plt.remove(text_obj[0])  # Borra el texto anterior
            msh = evt.object
            if not msh:
                text_obj[0] = vedo.Text2D(" ", pos='top-left')
            else:
                text_obj[0] = vedo.Text2D(f"{msh.polygon_name}", pos='top-left')
            plt.add(text_obj[0])
            plt.render()
        
        plt = vedo.Plotter(title="OpenSimula")
        plt.add_callback('mouse click', on_left_click)
        plt.show(*meshes, axes=1, viewup="z").close()

    def show_animation(self, texts, cosines , polygons_type="initial" ):
        vedo.settings.default_backend = 'vtk'
        meshes = []
        def slider_func(widget, event):
            idx = int(widget.value)
            widget.title = texts[idx]
            plt.remove( meshes.pop(0))
            cos = cosines[idx]
            self.calculate_shadows(cos, create_polygons=True)
            meshes.append(self.get_vedo_meshes(polygons_type))
            plt.add(meshes[0])

        # Show first frame
        self.calculate_shadows(cosines[0], create_polygons=True)
        meshes.append(self.get_vedo_meshes(polygons_type))
        plt = vedo.Plotter(title="OpenSimula", axes=1)  
        plt.add(meshes[0])
        plt.add_slider(
            slider_func,
            0, len(cosines)-1,  # slider range
            value=0,         # initial value
            pos="bottom-right",  # position of the slider
            title=texts[0]
        )
        plt.show(viewup="z").close()
        
    def delete_shadows(self):
        self.pol_sunny = []
        self.pol_shadows = []
        self.sunny_fraction = []

    def calculate_shadows(self, sun_position, create_polygons=True):
        self.sunny_fraction = []
        if create_polygons:
            self.pol_sunny = []
            self.pol_shadows = []

        for polygon in self.pol_3D:
            if polygon.calculate_shadows:
                sunny_polygons, shadow_polygons = polygon.get_sunny_shadow_polygon3D(
                    self, sun_position
                )
                if sunny_polygons is not None:
                    sunny_area = 0
                    for sunny_polygon in sunny_polygons:
                        if create_polygons:
                            self.pol_sunny.append(sunny_polygon)
                        sunny_area += sunny_polygon.area
                    self.sunny_fraction.append(sunny_area / polygon.area)
                else:
                    self.sunny_fraction.append(0)  # No sunny area
                if create_polygons:
                    if shadow_polygons is not None:
                        for shadow_polygon in shadow_polygons:
                            self.pol_shadows.append(shadow_polygon)
    
    def get_sunny_polygon_list(self):
        sunny_polygons = []
        for polygon in self.pol_3D:
            if polygon.calculate_shadows:
                sunny_polygons.append(polygon)
        return sunny_polygons
    
    def get_sunny_index(self, name):
        sunny_polygons = self.get_sunny_polygon_list()
        for i in range(len(sunny_polygons)):
            if sunny_polygons[i].name == name:
                return i
        return None
    
    def calculate_solar_tables(self):
        self._calculate_shadow_interpolation_table()
        self._calculate_diffuse_shadow()
        self.solar_tables_calculated = True

    def _calculate_shadow_interpolation_table(self):
        self.shadow_azimuth_grid = np.linspace(0, 350, 36)
        self.shadow_altitude_grid = np.linspace(-85, 85, 18)
        sunny_polygons = self.get_sunny_polygon_list()
        self.sunny_fraction_tables = np.zeros((len(sunny_polygons), 36, 18))
        j = 0
        for azimuth in self.shadow_azimuth_grid:
            azi_rd = math.radians(azimuth)
            k = 0
            for altitude in self.shadow_altitude_grid:
                alt_rd = math.radians(altitude)
                sun_position = np.array(
                    [
                        math.cos(alt_rd) * math.sin(azi_rd),
                        -math.cos(alt_rd) * math.cos(azi_rd),
                        math.sin(alt_rd),
                    ]
                )

                self.calculate_shadows(sun_position, create_polygons=False)
                sunny_frac = self.sunny_fraction
                for i in range(len(sunny_frac)):
                    self.sunny_fraction_tables[i][j][k] = sunny_frac[i]
                k = k + 1
            j = j + 1
        
        self.sunny_interpolation_functions = []
        for i in range(0, len(sunny_polygons)):
            self.sunny_interpolation_functions.append(
                RegularGridInterpolator(
                    (self.shadow_azimuth_grid, self.shadow_altitude_grid),
                    self.sunny_fraction_tables[i],
                    bounds_error=False,
                    fill_value=None,
                    method="cubic",
                )
            )
    
    def _calculate_diffuse_shadow(self):
        def integral(i,polygon_i):
            sunny_value = 0
            shadow_value = 0
            n = 0
            for j in range(len(self.shadow_azimuth_grid)):
                for k in range(len(self.shadow_altitude_grid)):
                    theta = polygon_i.get_angle_with_normal(
                        self.shadow_azimuth_grid[j], self.shadow_altitude_grid[k]
                    )
                    if theta < math.pi / 2:
                        f = 0.5 * math.sin(2 * theta)
                        sunny_value = sunny_value + f
                        shadow_value = (
                            shadow_value + f * self.sunny_fraction_tables[i][j][k]
                        )
                        n = n + 1
            return shadow_value / sunny_value

        self.shadow_diffuse_fraction = []
        sunny_polygon_list = self.get_sunny_polygon_list()
        for i in range(0, len(sunny_polygon_list)):
            polygon_i = sunny_polygon_list[i]
            self.shadow_diffuse_fraction.append(integral(i, polygon_i))
    
    def get_diffuse_sunny_fraction(self, sunny_i):
        if self.solar_tables_calculated == True:
            return self.shadow_diffuse_fraction[sunny_i]
        else:
            return 1

    def get_direct_interpolated_sunny_fraction(self, sunny_i, azi, alt):
        if self.solar_tables_calculated == True:
            if azi < 0:
                azi = azi + 360
            return self.sunny_interpolation_functions[sunny_i]((azi, alt))
        else:
            return 1      
    
    def get_direct_sunny_fraction(self, sunny_i):
        if self.sunny_fraction == []:
            return 1
        else:
            return self.sunny_fraction[sunny_i]
    
    def show_sunny_fraction(self, sunny_i):
        fig, ax = plt.subplots()
        X, Y = np.meshgrid(self.shadow_azimuth_grid, self.shadow_altitude_grid)
        ax.imshow(self.sunny_fraction_tables[sunny_i], vmin=0, vmax=1)
        plt.show()


