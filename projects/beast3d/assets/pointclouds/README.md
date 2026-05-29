# Point clouds for the interactive viewer

One folder per dataset, each holding the cloud plus its source view images:

```
pointclouds/
  cheese3d/             (Mouse)
    pointcloud.ply
    images/             # the multi-view input frames (optional, for reference)
  rat7m/                (Rat)
    pointcloud.ply
    images/
  chickadee/            (Chickadee)
    pointcloud.ply
    images/
  human36m/             (Human)
    pointcloud.ply
    images/
```

The viewer loads `assets/pointclouds/<dataset>/pointcloud.ply`. The folder name
is the dataset key — keep it exactly `cheese3d`, `rat7m`, `chickadee`, or
`human36m`. The `images/` subfolder is just for keeping the source views with
the cloud; the viewer doesn't read it (yet).

**PLY format:** ASCII or binary `.ply` with per-vertex position and color
(optionally an `opacity` property to enable the opacity-threshold slider):

```
element vertex N
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
property float opacity   # optional
```

The viewer (Three.js `PLYLoader`) auto-centers and scales each cloud, so the
coordinate system / units don't matter. Colors are read from the
`red`/`green`/`blue` properties (0–255). If a file is missing, the viewer shows
a friendly placeholder; you can also drag-and-drop a `.ply` onto the viewer to
preview locally before committing it.

## Getting the files from the `multi-view` repo

Two ready-made sources already produce this exact schema:

1. **Standard Gaussian PLY (directly compatible).**
   `src/utils/viz_utils.py::save_gaussian_ply_standard` already writes
   `red`/`green`/`blue` (uint8) alongside the splat parameters — the
   `gaussians.ply` files under `outputs/.../ply/sample_xxxxxx/` load as-is.
   Drop one per dataset as `<dataset>/pointcloud.ply` (e.g.
   `cheese3d/pointcloud.ply`).
   *Caveat:* these contain all splats (incl. background), so they look busier.

2. **Clean foreground cloud (recommended for a crisp viewer).**
   `src/encoding/inference_pc.py::extract_pointcloud` returns
   `{'xyz': (N,3), 'rgb': (N,3) in [0,1]}` after opacity/mask filtering — the
   same cloud behind the orbit renders. Convert it with `make_web_ply.py`:

   ```python
   from make_web_ply import save_web_ply
   pc = extract_pointcloud(output, opacity_threshold=0.05, gt_mask=mask)
   save_web_ply("cheese3d/pointcloud.ply", pc["xyz"], pc["rgb"])
   ```

   or from a saved `.npz` (arrays `xyz`, `rgb`):

   ```
   python make_web_ply.py --npz frame.npz --out cheese3d/pointcloud.ply
   ```
