#!/usr/bin/env python3
"""
Convert the per-dataset half-orbit 4D point clouds (xyz+rgb+opacity over time)
into compact web binaries for the interactive "Explore" panel.

Source npz (one per session) live next to the orbit-render videos, e.g.
  assets/<ds>_ind_video/<session>/render/<ds>_ind_half_orbit_pc_<session>.npz
with keys: xyz (sumPts,3) float, rgb (sumPts,3) [0,1], opacity (sumPts,) [0,1],
num_points (frames,) int. Frames are consecutive timesteps (a moving subject).

Output -> assets/pointclouds/<ds>/pc4d.bin  +  assets/pointclouds/pc4d.json
  bin layout: [ positions int16 (totalPts*3) | rgb uint8 (totalPts*3) | opacity uint8 (totalPts) ]
  positions are centered on the global centroid and scaled so the largest
  extent maps to [-1,1] (value = round((xyz-center)/half*32767)). The viewer
  flips Y/Z (OpenCV y-down -> three.js y-up) after decoding.
"""
import json
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.dirname(HERE)   # .../beast3d/assets

# dataset -> (npz path relative to ASSETS, max points/frame or None, playback fps)
SESSIONS = {
    'cheese3d':  ('cheese3d_ind_video/20231031_B31_chew_bl_000/render/cheese3d_ind_half_orbit_pc_20231031_B31_chew_bl_000.npz', 5000, 15),
    'chickadee': ('chickadee_ind_video/SLV143_230215_124523/render/chickadee_ind_half_orbit_pc_SLV143_230215_124523.npz', None, 15),
    'rat7m':     ('rat7m_ind_video/s1-d1/render/rat7m_ind_half_orbit_pc_s1-d1.npz', None, 20),
    'human36m':  ('human36m_ind_video/s_01_act_02/render/human36m_ind_half_orbit_pc_s_01_act_02.npz', None, 12),
}


def convert(ds, rel, cap, fps):
    z = np.load(os.path.join(ASSETS, rel), allow_pickle=True)
    xyz = z['xyz'].astype(np.float32)
    rgb = z['rgb'].astype(np.float32)
    op = z['opacity'].astype(np.float32)
    npf = z['num_points'].astype(np.int64)
    off = np.zeros(len(npf) + 1, np.int64)
    off[1:] = np.cumsum(npf)

    xs, cs, os_, counts = [], [], [], []
    for f in range(len(npf)):
        a, b = off[f], off[f + 1]
        fx, fc, fo = xyz[a:b], rgb[a:b], op[a:b]
        if cap is not None and fx.shape[0] > cap:           # keep highest-opacity points
            idx = np.argpartition(-fo, cap - 1)[:cap]
            fx, fc, fo = fx[idx], fc[idx], fo[idx]
        xs.append(fx); cs.append(fc); os_.append(fo); counts.append(int(fx.shape[0]))
    XYZ = np.concatenate(xs); RGB = np.concatenate(cs); OP = np.concatenate(os_)
    n = XYZ.shape[0]

    center = (XYZ.min(0) + XYZ.max(0)) / 2.0
    half = float(np.max(XYZ.max(0) - XYZ.min(0))) / 2.0 or 1.0
    pos = np.clip(np.round((XYZ - center) / half * 32767.0), -32767, 32767).astype('<i2')
    rgb_u8 = np.clip(np.round(RGB * 255.0), 0, 255).astype(np.uint8)
    op_u8 = np.clip(np.round(OP * 255.0), 0, 255).astype(np.uint8)

    out_dir = os.path.join(HERE, ds)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'pc4d.bin'), 'wb') as fh:
        fh.write(pos.tobytes()); fh.write(rgb_u8.tobytes()); fh.write(op_u8.tobytes())
    return {'frames': len(counts), 'counts': counts, 'totalPts': n, 'fps': fps}


def main():
    meta = {}
    for ds, (rel, cap, fps) in SESSIONS.items():
        meta[ds] = convert(ds, rel, cap, fps)
        m = meta[ds]
        sz = os.path.getsize(os.path.join(HERE, ds, 'pc4d.bin')) / 1e6
        print(f"  {ds:10s} frames={m['frames']:3d} pts={m['totalPts']:>8,} -> {sz:.1f} MB")
    with open(os.path.join(HERE, 'pc4d.json'), 'w') as f:
        json.dump(meta, f)
    print("wrote pc4d.json")


if __name__ == '__main__':
    main()
