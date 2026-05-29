#!/usr/bin/env python3
"""
Convert the chickadee encoding results into compact web assets for the
interactive 4D point cloud + neural raster on the project page.

Inputs (this folder):
  chickadee/full_predictions.npz        pred/target (W,T,N), splits, names
  chickadee/pointcloud_4d.npz           xyz (sum_pts,3), num_points, frame ids
  chickadee/keypoints_f*.npz            keypoints (F,18,3)

Outputs -> chickadee/web/:
  meta.json              all metadata + small arrays
  raster_full_u8.bin     [GT(N,Wf) | PRED(N,Wf) | BEH(Kb,Wf)] uint8, row-major
  raster_seg_u8.bin      [GT(N,Ls) | PRED(N,Ls)] uint8 (segment, full-res)
  pc_xyz_i16.bin         int16 (totalPts,3) for the segment

Everything is frame-aligned over F=54000 frames @ 60 fps. Neural windows tile
contiguously, so target/pred reshape to (F,N) in time order. Rasters are
gaussian-smoothed (sigma=2) then per-row z-scored, clipped to +/-VLIM and
mapped to uint8. Neurons are ordered by the 1st PCA component of smoothed GT
(dependency-free stand-in for rastermap) and that order is shared by all panels.
"""
import json
import os
import numpy as np
from scipy.ndimage import gaussian_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'chickadee')
OUT = os.path.join(SRC, 'web')

FPS = 60
SMOOTH_SIGMA = 2.0
VLIM = 2.5
FULL_BIN = 10          # time downsample for the overview raster (54000 -> 5400)
SEG_LEN = 3600         # segment length in frames (3600 = 60 s @ 60 fps)
SEG_START = None       # None -> auto-pick the most-active window of SEG_LEN


def zscore_rows(a, eps=1e-8):
    m = a.mean(axis=1, keepdims=True)
    s = a.std(axis=1, keepdims=True)
    return (a - m) / np.maximum(s, eps)


def to_u8(z):
    """z-scored float -> uint8 with [-VLIM, VLIM] mapped to [0, 255]."""
    t = np.clip((z + VLIM) / (2 * VLIM), 0.0, 1.0)
    return np.round(t * 255).astype(np.uint8)


def pca_order(mat):
    """Row permutation by sign-consistent 1st left singular vector."""
    c = mat - mat.mean(axis=1, keepdims=True)
    U, S, Vt = np.linalg.svd(c, full_matrices=False)
    return np.argsort(U[:, 0])


def main():
    os.makedirs(OUT, exist_ok=True)

    # ---- neural ----
    P = np.load(os.path.join(SRC, 'full_predictions.npz'), allow_pickle=True)
    pred = P['pred'].astype(np.float32)      # (W,T,N)
    target = P['target'].astype(np.float32)  # (W,T,N)
    W, T, N = pred.shape
    F = W * T
    names = [str(x) for x in P['cluster_names']]
    split_names = [str(x) for x in P['split_names']]
    # windows already sorted by start_frames -> reshape is time order
    gt = target.reshape(F, N).T              # (N,F)
    pr = pred.reshape(F, N).T                # (N,F)

    gt_s = gaussian_filter1d(gt, SMOOTH_SIGMA, axis=1, mode='nearest')
    pr_s = gaussian_filter1d(pr, SMOOTH_SIGMA, axis=1, mode='nearest')
    gt_z = zscore_rows(gt_s)
    pr_z = zscore_rows(pr_s)

    order = pca_order(gt_z)
    gt_z, pr_z = gt_z[order], pr_z[order]
    names_ord = [names[i] for i in order]

    # per-frame split id (0/1/2) from per-window split_id
    split_id = P['split_id'].astype(np.int8)
    frame_split = np.repeat(split_id, T)     # (F,)

    # ---- behavior: per-joint speed (units/sec) ----
    kp_files = [f for f in os.listdir(SRC) if f.startswith('keypoints_') and f.endswith('.npz')]
    KP = np.load(os.path.join(SRC, kp_files[0]), allow_pickle=True)['keypoints'].astype(np.float32)
    KP = KP[:F]                              # (F,18,3)
    vel = np.zeros((F, KP.shape[1]), np.float32)
    vel[1:-1] = np.linalg.norm((KP[2:] - KP[:-2]) * (FPS / 2.0), axis=2)
    vel[0], vel[-1] = vel[1], vel[-2]
    beh = vel.T                              # (Kb,F)
    beh_z = zscore_rows(gaussian_filter1d(beh, SMOOTH_SIGMA, axis=1, mode='nearest'))
    beh_z = beh_z[pca_order(beh_z)]
    Kb = beh_z.shape[0]

    # ---- downsample full timeline (mean over bins) ----
    Wf = F // FULL_BIN
    def binned(z):
        return z[:, :Wf * FULL_BIN].reshape(z.shape[0], Wf, FULL_BIN).mean(axis=2)
    gt_f, pr_f, beh_f = binned(gt_z), binned(pr_z), binned(beh_z)
    split_f = frame_split[:Wf * FULL_BIN].reshape(Wf, FULL_BIN)[:, 0]

    full_u8 = np.concatenate([to_u8(beh_f), to_u8(gt_f), to_u8(pr_f)], axis=0)
    full_u8.tofile(os.path.join(OUT, 'raster_full_u8.bin'))

    # ---- pick segment: the SEG_LEN window where BEAST3D best predicts GT,
    # scored by mean R^2 (squared Pearson, per neuron) over the window.
    # Pearson is scale-invariant, which matters since pred is a rate and target
    # is spike counts. Sliding window stats come from cumulative sums.
    if SEG_START is None:
        L = SEG_LEN
        p, t = pr_s.astype(np.float64), gt_s.astype(np.float64)   # smoothed (N,F)

        def csum(a):
            c = np.zeros((a.shape[0], a.shape[1] + 1))
            c[:, 1:] = np.cumsum(a, axis=1)
            return c

        Cp, Ct, Cp2, Ct2, Cpt = (csum(p), csum(t), csum(p * p),
                                  csum(t * t), csum(p * t))
        win = lambda C: C[:, L:] - C[:, :-L]          # (N, S) window sums
        Sp, St, Sp2, St2, Spt = win(Cp), win(Ct), win(Cp2), win(Ct2), win(Cpt)
        num = L * Spt - Sp * St
        den = np.sqrt(np.maximum(L * Sp2 - Sp * Sp, 0) *
                      np.maximum(L * St2 - St * St, 0))
        with np.errstate(divide='ignore', invalid='ignore'):
            r = np.where(den > 1e-12, num / den, 0.0)
        meanr2 = np.nanmean(r * r, axis=0)            # (S,) mean over neurons
        s0 = int(np.argmax(meanr2))
        print(f'selected by R^2: mean r^2 = {meanr2[s0]:.3f}')
    else:
        s0 = int(SEG_START)
    s1 = s0 + SEG_LEN
    print(f'segment: frames [{s0}, {s1}) = {s0/FPS:.1f}-{s1/FPS:.1f}s ({SEG_LEN/FPS:.0f}s)')

    # ---- segment raster (full-res): behavior speed, GT, BEAST3D ----
    seg_u8 = np.concatenate([to_u8(beh_z[:, s0:s1]),
                             to_u8(gt_z[:, s0:s1]),
                             to_u8(pr_z[:, s0:s1])], axis=0)
    seg_u8.tofile(os.path.join(OUT, 'raster_seg_u8.bin'))

    # ---- 4D point cloud for the segment ----
    PC = np.load(os.path.join(SRC, 'pointcloud_4d.npz'), allow_pickle=True)
    npts = PC['num_points'].astype(np.int64)
    off = np.zeros(len(npts) + 1, np.int64)
    off[1:] = np.cumsum(npts)
    xyz_all = PC['xyz']
    seg_counts = npts[s0:s1].tolist()

    # Center each frame on its own centroid so the bird stays in view (it
    # translates a lot during the bout). Normalize by a single global scale so
    # relative per-frame size changes (pose, distance) are preserved.
    frames = [xyz_all[off[f]:off[f + 1]].astype(np.float32) for f in range(s0, s1)]
    centered = [p - p.mean(axis=0, keepdims=True) for p in frames]
    half = float(max(np.abs(c).max() for c in centered)) or 1.0
    seg_xyz = np.concatenate(centered, axis=0)
    q = np.clip(np.round(seg_xyz / half * 32767.0), -32767, 32767).astype('<i2')
    q.tofile(os.path.join(OUT, 'pc_xyz_i16.bin'))
    center = [0.0, 0.0, 0.0]

    meta = {
        'fps': FPS, 'vlim': VLIM, 'frames': F,
        'neurons': {'count': N, 'names': names_ord},
        'behavior': {'count': Kb},
        'full': {'width': Wf, 'bin': FULL_BIN, 'rowsGt': N, 'rowsPred': N, 'rowsBeh': Kb},
        'seg': {'start': s0, 'len': SEG_LEN, 'width': SEG_LEN,
                'rowsBeh': Kb, 'rowsGt': N, 'rowsPred': N},
        'split': {'names': split_names,
                  'colors': ['#e7ecf3', '#243e36', '#7ca982'],
                  'full': split_f.astype(np.uint8).tolist()},
        'pc': {'center': center, 'half': half, 'centeredPerFrame': True,
               'len': SEG_LEN, 'counts': seg_counts,
               'totalPts': int(seg_xyz.shape[0])},
    }
    with open(os.path.join(OUT, 'meta.json'), 'w') as f:
        json.dump(meta, f)

    def mb(p):
        return os.path.getsize(os.path.join(OUT, p)) / 1e6
    print('wrote ->', OUT)
    for p in ['meta.json', 'raster_full_u8.bin', 'raster_seg_u8.bin', 'pc_xyz_i16.bin']:
        print(f'  {p:22s} {mb(p):.2f} MB')


if __name__ == '__main__':
    main()
