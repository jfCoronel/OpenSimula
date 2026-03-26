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

    # ── Plotly helpers (jupyter mode) ──────────────────────────────────────

    def _rgb_str_(self, color_name):
        rgb = vedo.colors.get_color(color_name)
        return f"rgb({int(rgb[0]*255)},{int(rgb[1]*255)},{int(rgb[2]*255)})"

    def _polygon_to_plotly_(self, polygon_3D):
        """Returns (go.Mesh3d, go.Scatter3d outline) for a single Polygon_3D."""
        import plotly.graph_objects as go
        points, faces = polygon_3D._triangulate_()
        pts = np.array(points)
        fcs = np.array(faces)
        color = self._rgb_str_(polygon_3D.color)
        mesh = go.Mesh3d(
            x=pts[:, 0], y=pts[:, 1], z=pts[:, 2],
            i=fcs[:, 0], j=fcs[:, 1], k=fcs[:, 2],
            color=color, opacity=polygon_3D.opacity,
            name=polygon_3D.name,
            hovertemplate=f"<b>{polygon_3D.name}</b><extra></extra>",
            flatshading=True,
            lighting=dict(ambient=0.85, diffuse=0.5, specular=0.05),
        )
        boundary = np.array(polygon_3D.polygon3D)
        xs = list(boundary[:, 0]) + [boundary[0, 0], None]
        ys = list(boundary[:, 1]) + [boundary[0, 1], None]
        zs = list(boundary[:, 2]) + [boundary[0, 2], None]
        outline = go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode="lines",
            line=dict(color="black", width=2),
            showlegend=False, hoverinfo="skip",
        )
        return mesh, outline

    def _merge_to_plotly_(self, polygon_list, name=""):
        """Merge multiple Polygon_3D into a single go.Mesh3d (for animation frames)."""
        import plotly.graph_objects as go
        if not polygon_list:
            return go.Mesh3d(x=[0], y=[0], z=[0], i=[], j=[], k=[],
                             visible=False, showlegend=False, hoverinfo="skip")
        all_pts, all_i, all_j, all_k, all_colors = [], [], [], [], []
        offset = 0
        for pol in polygon_list:
            points, faces = pol._triangulate_()
            pts = np.array(points)
            fcs = np.array(faces)
            all_pts.append(pts)
            all_i.extend((fcs[:, 0] + offset).tolist())
            all_j.extend((fcs[:, 1] + offset).tolist())
            all_k.extend((fcs[:, 2] + offset).tolist())
            c = self._rgb_str_(pol.color)
            all_colors.extend([c] * len(fcs))
            offset += len(pts)
        pts_arr = np.concatenate(all_pts, axis=0)
        return go.Mesh3d(
            x=pts_arr[:, 0], y=pts_arr[:, 1], z=pts_arr[:, 2],
            i=all_i, j=all_j, k=all_k,
            facecolor=all_colors,
            flatshading=True, name=name,
            hoverinfo="skip",
            lighting=dict(ambient=0.85, diffuse=0.5, specular=0.05),
        )

    def _scene_bounds_(self, pols):
        """Return (xmin, xmax, ymin, ymax, zmin, zmax) for a list of Polygon_3D."""
        all_pts = np.concatenate([np.array(p.polygon3D) for p in pols if len(p.polygon3D) > 0], axis=0)
        return (all_pts[:, 0].min(), all_pts[:, 0].max(),
                all_pts[:, 1].min(), all_pts[:, 1].max(),
                all_pts[:, 2].min(), all_pts[:, 2].max())

    def _zero_plane_traces_(self, pols):
        """Return thin-line Scatter3d outlines for the x=0, y=0, z=0 planes."""
        import plotly.graph_objects as go
        if not pols:
            return []
        xmin, xmax, ymin, ymax, zmin, zmax = self._scene_bounds_(pols)
        style = dict(color="rgba(100,100,100,0.5)", width=1)
        traces = []

        def rect_trace(xs, ys, zs):
            return go.Scatter3d(
                x=xs, y=ys, z=zs,
                mode="lines",
                line=style,
                showlegend=False, hoverinfo="skip",
            )

        # z=0 plane outline (only if 0 is within z range)
        if zmin <= 0 <= zmax:
            traces.append(rect_trace(
                [xmin, xmax, xmax, xmin, xmin],
                [ymin, ymin, ymax, ymax, ymin],
                [0, 0, 0, 0, 0],
            ))
        # x=0 plane outline
        if xmin <= 0 <= xmax:
            traces.append(rect_trace(
                [0, 0, 0, 0, 0],
                [ymin, ymax, ymax, ymin, ymin],
                [zmin, zmin, zmax, zmax, zmin],
            ))
        # y=0 plane outline
        if ymin <= 0 <= ymax:
            traces.append(rect_trace(
                [xmin, xmax, xmax, xmin, xmin],
                [0, 0, 0, 0, 0],
                [zmin, zmin, zmax, zmax, zmin],
            ))
        return traces

    def _plotly_scene_layout_(self):
        import plotly.graph_objects as go
        axis_style = dict(
            showbackground=False,
            tickfont=dict(size=9, color="gray"),
            title_font=dict(size=10, color="gray"),
        )
        return go.Layout(
            scene=dict(
                xaxis=dict(title="X [m]", **axis_style),
                yaxis=dict(title="Y [m]", **axis_style),
                zaxis=dict(title="Z [m]", **axis_style),
                aspectmode="data",
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
        )

    # ── Public show methods ─────────────────────────────────────────────────

    def show(self, polygons_type="initial", jupyter=False):
        if jupyter:
            import plotly.graph_objects as go
            if polygons_type == "initial":
                pols = [p for p in self.pol_3D if p.visible]
            elif polygons_type == "Building_shadows":
                pols = (list(self.pol_sunny) + list(self.pol_shadows) +
                        [p for p in self.pol_3D if p.visible and not p.calculate_shadows])
            elif polygons_type == "sunny":
                pols = list(self.pol_sunny)
            elif polygons_type == "shadows":
                pols = list(self.pol_shadows)
            else:
                pols = list(self.pol_sunny) + list(self.pol_shadows)
            traces = []
            for pol in pols:
                mesh, outline = self._polygon_to_plotly_(pol)
                traces.extend([mesh, outline])
            traces.extend(self._zero_plane_traces_(pols))
            go.Figure(data=traces, layout=self._plotly_scene_layout_()).show()
        else:
            vedo.settings.default_backend = "vtk"
            meshes = self.get_vedo_meshes(polygons_type)
            text_obj = [None]

            def on_left_click(evt):
                if text_obj[0] is not None:
                    vp.remove(text_obj[0])
                msh = evt.object
                if not msh:
                    text_obj[0] = vedo.Text2D(" ", pos='top-left')
                else:
                    text_obj[0] = vedo.Text2D(f"{msh.polygon_name}", pos='top-left')
                vp.add(text_obj[0])
                vp.render()

            vp = vedo.Plotter(title="opensimula")
            vp.add_callback('mouse click', on_left_click)
            vp.show(*meshes, axes=1, viewup="z").close()

    def show_animation(self, texts, cosines, polygons_type="initial", jupyter=False):
        if jupyter:
            import plotly.graph_objects as go

            # Static traces: surfaces that don't participate in shadow calculation
            static_pols = [p for p in self.pol_3D if p.visible and not p.calculate_shadows]
            static_traces = []
            for pol in static_pols:
                mesh, outline = self._polygon_to_plotly_(pol)
                static_traces.extend([mesh, outline])
            all_pols = list(self.pol_3D) + list(self.pol_sunny) + list(self.pol_shadows)
            static_traces.extend(self._zero_plane_traces_([p for p in all_pols if len(p.polygon3D) > 0]))
            n_static = len(static_traces)

            # Build frames (sunny + shadow merged meshes update per frame)
            self.calculate_shadows(cosines[0], create_polygons=True)
            init_sunny = self._merge_to_plotly_(self.pol_sunny, "sunny")
            init_shadow = self._merge_to_plotly_(self.pol_shadows, "shadow")

            frames = []
            for i, (cos, text) in enumerate(zip(cosines, texts)):
                self.calculate_shadows(cos, create_polygons=True)
                frames.append(go.Frame(
                    data=[self._merge_to_plotly_(self.pol_sunny, "sunny"),
                          self._merge_to_plotly_(self.pol_shadows, "shadow")],
                    traces=[n_static, n_static + 1],
                    name=str(i),
                    layout=go.Layout(title_text=text),
                ))

            layout = self._plotly_scene_layout_()
            layout.update(
                title_text=texts[0],
                margin=dict(l=0, r=0, t=30, b=80),
                updatemenus=[dict(
                    type="buttons", direction="left",
                    pad={"r": 10, "t": 20}, x=0.1, y=0,
                    buttons=[
                        dict(label="▶ Play", method="animate",
                             args=[None, {"frame": {"duration": 800, "redraw": True},
                                          "fromcurrent": True}]),
                        dict(label="⏸ Pause", method="animate",
                             args=[[None], {"frame": {"duration": 0}, "mode": "immediate"}]),
                    ],
                )],
                sliders=[dict(
                    active=0,
                    steps=[dict(
                        method="animate",
                        args=[[str(i)], {"frame": {"duration": 0, "redraw": True},
                                         "mode": "immediate"}],
                        label=texts[i],
                    ) for i in range(len(texts))],
                    x=0, y=0, len=1.0, pad={"b": 10, "t": 30},
                )],
            )
            go.Figure(
                data=static_traces + [init_sunny, init_shadow],
                layout=layout,
                frames=frames,
            ).show()
        else:
            vedo.settings.default_backend = "vtk"
            meshes = []

            def slider_func(widget, event):
                idx = int(widget.value)
                widget.title = texts[idx]
                vp.remove(meshes.pop(0))
                cos = cosines[idx]
                self.calculate_shadows(cos, create_polygons=True)
                meshes.append(self.get_vedo_meshes(polygons_type))
                vp.add(meshes[0])

            self.calculate_shadows(cosines[0], create_polygons=True)
            meshes.append(self.get_vedo_meshes(polygons_type))
            vp = vedo.Plotter(title="opensimula", axes=1)
            vp.add(meshes[0])
            vp.add_slider(
                slider_func,
                0, len(cosines) - 1,
                value=0,
                pos="bottom-right",
                title=texts[0],
            )
            vp.show(viewup="z").close()
        
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


