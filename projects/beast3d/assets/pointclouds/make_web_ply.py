#!/usr/bin/env python3
"""
make_web_ply.py — convert a BEAST3D point cloud to a web-ready colored .ply
for the interactive viewer on the project page.

The viewer reads a binary .ply with per-vertex position + 8-bit color:
    x, y, z  (float32)   red, green, blue  (uint8)

This is the SAME schema your repo already writes via
`src/utils/viz_utils.py::save_gaussian_ply_standard` (it emits red/green/blue),
so those `gaussians.ply` files load directly. Use this script instead when you
want the *clean foreground* cloud from
`src/encoding/inference_pc.py::extract_pointcloud`, which returns {'xyz', 'rgb'}
(rgb in [0, 1]) after opacity/mask filtering — it matches the orbit renders.

Usage
-----
# From an .npz that contains arrays `xyz` (N,3) and `rgb` (N,3, in [0,1] or [0,255]):
python make_web_ply.py --npz frame.npz --out cheese3d.ply

# Or import and call directly from your inference code:
#   from make_web_ply import save_web_ply
#   pc = extract_pointcloud(output, ...)        # {'xyz':(N,3), 'rgb':(N,3) in [0,1]}
#   save_web_ply('cheese3d.ply', pc['xyz'], pc['rgb'])

Name the outputs exactly: cheese3d.ply, rat7m.ply, chickadee.ply, human36m.ply
and drop them next to this script.
"""
import argparse
import numpy as np


def save_web_ply(path, xyz, rgb):
    """Write a binary little-endian .ply with float xyz + uint8 rgb.

    xyz: (N, 3) array.
    rgb: (N, 3) array, either floats in [0, 1] or ints in [0, 255].
    """
    xyz = np.asarray(xyz, dtype=np.float32).reshape(-1, 3)
    rgb = np.asarray(rgb).reshape(-1, 3)
    if rgb.dtype.kind == 'f' or rgb.max() <= 1.0 + 1e-6:
        rgb = np.clip(rgb, 0.0, 1.0) * 255.0
    rgb = np.clip(rgb, 0, 255).round().astype(np.uint8)
    assert xyz.shape[0] == rgb.shape[0], "xyz and rgb must have the same length"
    n = xyz.shape[0]

    vertex = np.empty(n, dtype=[
        ("x", "<f4"), ("y", "<f4"), ("z", "<f4"),
        ("red", "u1"), ("green", "u1"), ("blue", "u1"),
    ])
    vertex["x"], vertex["y"], vertex["z"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    vertex["red"], vertex["green"], vertex["blue"] = rgb[:, 0], rgb[:, 1], rgb[:, 2]

    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        f"element vertex {n}\n"
        "property float x\nproperty float y\nproperty float z\n"
        "property uchar red\nproperty uchar green\nproperty uchar blue\n"
        "end_header\n"
    ).encode("ascii")

    with open(path, "wb") as f:
        f.write(header)
        f.write(vertex.tobytes())
    print(f"wrote {n:,} points -> {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--npz", required=True,
                    help="npz with arrays 'xyz' (N,3) and 'rgb' (N,3). "
                         "If a 4D npz with stacked frames, pass --frame to slice one.")
    ap.add_argument("--out", required=True, help="output .ply path")
    ap.add_argument("--frame", type=int, default=None,
                    help="optional frame index if the npz stacks multiple frames")
    args = ap.parse_args()

    data = np.load(args.npz)
    xyz, rgb = data["xyz"], data["rgb"]
    if args.frame is not None and xyz.ndim == 3:
        xyz, rgb = xyz[args.frame], rgb[args.frame]
    save_web_ply(args.out, xyz, rgb)


if __name__ == "__main__":
    main()
