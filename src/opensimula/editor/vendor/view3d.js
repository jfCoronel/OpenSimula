// 3D view helpers shared by the project editor and the results viewer: the
// scene layout, the camera and the geometry of the plotly traces. Bundled into
// each widget by esbuild (npm run build).

// Same look as Project.show_3D(jupyter=True); see _plotly_scene_layout_().
export const AXIS_STYLE = {
  showbackground: true,
  backgroundcolor: "rgb(220, 220, 220)",
  tickfont: { size: 9, color: "gray" },
  title: { font: { size: 10, color: "gray" } },
};

export const VIEW_LAYOUT = {
  paper_bgcolor: "rgb(235, 235, 235)",
  scene: {
    xaxis: { title: { text: "X [m]" }, ...AXIS_STYLE },
    yaxis: { title: { text: "Y [m]" }, ...AXIS_STYLE },
    zaxis: { title: { text: "Z [m]" }, ...AXIS_STYLE },
    aspectmode: "data",
    bgcolor: "rgb(235, 235, 235)",
  },
  margin: { l: 0, r: 0, t: 0, b: 0 },
  showlegend: false,
};

export const column = (rows, index) => rows.map((row) => row[index]);

export function modelBounds(geometry) {
  const low = [Infinity, Infinity, Infinity];
  const high = [-Infinity, -Infinity, -Infinity];
  for (const mesh of geometry.meshes || []) {
    for (const point of mesh.points) {
      for (let axis = 0; axis < 3; axis += 1) {
        if (point[axis] < low[axis]) low[axis] = point[axis];
        if (point[axis] > high[axis]) high[axis] = point[axis];
      }
    }
  }
  if (!Number.isFinite(low[0])) return null;
  return { low, high, size: high.map((value, axis) => Math.max(value - low[axis], 1e-6)) };
}

export function axisRanges(bounds) {
  // Pinned to the whole model, not to what a filter leaves visible. Otherwise
  // aspectmode "data" rebuilds the scene box around one space, which blows it
  // up to fill the panel and leaves the camera pointing at the wrong place.
  // Held fixed, an isolated space stays where it belongs, at its real size.
  const margin = Math.max(...bounds.size) * 0.05;
  return [0, 1, 2].map((axis) => [
    bounds.low[axis] - margin,
    bounds.high[axis] + margin,
  ]);
}

export function defaultCamera(bounds) {
  // With aspectmode "data" plotly stretches the scene box to the shape of the
  // model, normalised to unit volume, so a building wider than it is tall gets
  // a box bigger than the unit cube. Its default eye is placed for that cube
  // and ends up inside the building; the distance has to follow the box.
  const unit = Math.cbrt(bounds.size[0] * bounds.size[1] * bounds.size[2]);
  const reach = Math.max(...bounds.size.map((value) => value / unit));
  // Looking down from the south east, the usual angle to read a building from.
  // The distance was set by eye against the HULC model: closer than this and a
  // building of its proportions starts to touch the bottom of the panel.
  return { eye: { x: 1.1 * reach, y: -1.1 * reach, z: 0.76 * reach } };
}

export function faceNormal(points, faces) {
  const [a, b, c] = faces[0].map((index) => points[index]);
  const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
  const v = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
  const n = [
    u[1] * v[2] - u[2] * v[1],
    u[2] * v[0] - u[0] * v[2],
    u[0] * v[1] - u[1] * v[0],
  ];
  const length = Math.hypot(n[0], n[1], n[2]) || 1;
  return n.map((value) => value / length);
}

// Lifted off the surface it covers, or the two coplanar faces fight for depth
// and the highlight speckles.
export const HIGHLIGHT_LIFT = 0.006;

export function highlightGeometry(mesh) {
  if (!mesh) return { x: [], y: [], z: [], i: [], j: [], k: [] };
  const n = faceNormal(mesh.points, mesh.faces);
  // One sheet on each side. Lifting to one side only hides the highlight
  // behind the surface itself when looked at from the other: a floor is
  // normally seen from below, and the sheet was going on top of it.
  const shift = (sign) =>
    mesh.points.map((p) => [
      p[0] + sign * n[0] * HIGHLIGHT_LIFT,
      p[1] + sign * n[1] * HIGHLIGHT_LIFT,
      p[2] + sign * n[2] * HIGHLIGHT_LIFT,
    ]);
  const points = [...shift(1), ...shift(-1)];
  const behind = mesh.points.length;
  const faces = [
    ...mesh.faces,
    ...mesh.faces.map((face) => face.map((index) => index + behind)),
  ];
  return {
    x: column(points, 0),
    y: column(points, 1),
    z: column(points, 2),
    i: column(faces, 0),
    j: column(faces, 1),
    k: column(faces, 2),
  };
}

// ____________________ plotly from the kernel ____________________

// The gl3d bundle of plotly (1.7 MB) ships with the package as
// static/plotly3d.js and is sent by Python, as a message buffer, the first time
// a 3D view is opened. Fetching it from a CDN is blocked by the CSP of VS Code
// notebooks; importing it from a blob: URL is how anywidget loads the widget
// itself, so it is allowed wherever the widget runs. Kept on globalThis, so it
// is received once per page whatever the number of widgets.
const PLOTLY_KEY = "__opensimula_plotly__";

export function plotlyLoaded() {
  return globalThis[PLOTLY_KEY] || null;
}

export function receivePlotly(buffer) {
  if (globalThis[PLOTLY_KEY]) return globalThis[PLOTLY_KEY];
  const bytes = buffer instanceof DataView ? new Uint8Array(buffer.buffer, buffer.byteOffset, buffer.byteLength) : buffer;
  const url = URL.createObjectURL(new Blob([bytes], { type: "text/javascript" }));
  globalThis[PLOTLY_KEY] = import(/* webpackIgnore: true */ url).then(
    (module) => {
      URL.revokeObjectURL(url);
      return module.default || module;
    },
    (err) => {
      delete globalThis[PLOTLY_KEY]; // so that it can be sent again
      throw err;
    },
  );
  return globalThis[PLOTLY_KEY];
}
