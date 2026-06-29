import os
import json
import math
import numpy as np
import pandas as pd


def solve(data_folder: str) -> int:
    comp = pd.read_csv(os.path.join(data_folder, 'input_component.csv'))
    size = pd.read_csv(os.path.join(data_folder, 'input_size.csv'))

    pcb_w = size['pcb_size'].iloc[0]
    pcb_h = size['pcb_size'].iloc[1]
    fov_w = size['fov_size'].iloc[0]
    fov_h = size['fov_size'].iloc[1]
    side_fov_w = fov_w / 2.0
    side_fov_h = fov_h / 2.0

    n = len(comp)
    assigned = [False] * n

    comp_cx = ((comp['tl_x'] + comp['br_x']) / 2.0).values
    comp_cy = ((comp['tl_y'] + comp['br_y']) / 2.0).values
    comp_w = (comp['br_x'] - comp['tl_x']).values
    comp_h = (comp['br_y'] - comp['tl_y']).values
    comp_type = comp['type'].astype(int).values
    comp_side = comp['side'].astype(int).values if 'side' in comp.columns else np.zeros(n, dtype=int)
    comp_step = comp['step'].astype(int).values if 'step' in comp.columns else np.zeros(n, dtype=int)
    comp_tl_x = comp['tl_x'].values
    comp_tl_y = comp['tl_y'].values
    comp_br_x = comp['br_x'].values
    comp_br_y = comp['br_y'].values

    is_big = np.where(comp_side == 1,
                      (comp_w > side_fov_w) | (comp_h > side_fov_h),
                      (comp_w > fov_w) | (comp_h > fov_h))

    fovs = []

    # --- Step 1: Fiducial (type=2) --- 1 per FOV
    for i in range(n):
        if comp_type[i] == 2 and not is_big[i]:
            fx = comp_cx[i]
            fy = comp_cy[i]
            fovs.append({'x': fx, 'y': fy, 'comp_idx': [i], 'step': comp_step[i]})
            assigned[i] = True

    # --- Step 2: Greedy placement (origin-distance order) ---
    dist = np.sqrt(comp_cx ** 2 + comp_cy ** 2)
    order = np.argsort(dist)

    for seed_i in order:
        if assigned[seed_i] or is_big[seed_i] or comp_type[seed_i] == 2:
            continue

        fx = comp_tl_x[seed_i] + fov_w / 2
        fy = comp_tl_y[seed_i] + fov_h / 2

        fov_tl_x = fx - fov_w / 2
        fov_tl_y = fy - fov_h / 2
        fov_br_x = fx + fov_w / 2
        fov_br_y = fy + fov_h / 2

        s_tl_x = fx - side_fov_w / 2
        s_tl_y = fy - side_fov_h / 2
        s_br_x = fx + side_fov_w / 2
        s_br_y = fy + side_fov_h / 2

        seed_step = comp_step[seed_i]
        covered = []

        for j in order:
            if assigned[j] or is_big[j] or comp_type[j] == 2:
                continue
            if comp_step[j] != seed_step:
                continue

            if comp_side[j] == 1:
                chk_tl_x, chk_tl_y = s_tl_x, s_tl_y
                chk_br_x, chk_br_y = s_br_x, s_br_y
            else:
                chk_tl_x, chk_tl_y = fov_tl_x, fov_tl_y
                chk_br_x, chk_br_y = fov_br_x, fov_br_y

            tol = 1e-5
            if (chk_tl_x - tol <= comp_tl_x[j] and chk_tl_y - tol <= comp_tl_y[j] and
                    chk_br_x + tol >= comp_br_x[j] and chk_br_y + tol >= comp_br_y[j]):
                covered.append(j)

        if covered:
            for j in covered:
                assigned[j] = True
            fovs.append({'x': fx, 'y': fy, 'comp_idx': covered, 'step': seed_step})

    # --- Step 3: Big components --- tiling
    for i in range(n):
        if assigned[i]:
            continue

        cw, ch = comp_w[i], comp_h[i]
        eff_w = side_fov_w if comp_side[i] == 1 else fov_w
        eff_h = side_fov_h if comp_side[i] == 1 else fov_h
        n_x = math.ceil(cw / eff_w) if cw > eff_w else 1
        n_y = math.ceil(ch / eff_h) if ch > eff_h else 1

        if n_x == 1 and n_y == 1:
            fx = comp_cx[i]
            fy = comp_cy[i]
            fovs.append({'x': fx, 'y': fy, 'comp_idx': [i], 'step': comp_step[i]})
        else:
            for gx in range(n_x):
                for gy in range(n_y):
                    fx = comp_tl_x[i] + eff_w / 2 + gx * eff_w
                    fy = comp_tl_y[i] + eff_h / 2 + gy * eff_h
                    fx = min(fx, comp_br_x[i] - eff_w / 2)
                    fy = min(fy, comp_br_y[i] - eff_h / 2)
                    fovs.append({'x': fx, 'y': fy, 'comp_idx': [i], 'step': comp_step[i]})
        assigned[i] = True

    # --- Step 4: Nearest-neighbor ordering (type DESC) ---
    for f in fovs:
        f['type'] = max((comp_type[j] for j in f['comp_idx']), default=0)

    ordered = []
    for t in sorted(set(f['type'] for f in fovs), reverse=True):
        group = [f for f in fovs if f['type'] == t]
        while group:
            if not ordered:
                best = min(range(len(group)),
                           key=lambda j: group[j]['x'] ** 2 + group[j]['y'] ** 2)
            else:
                lx, ly = ordered[-1]['x'], ordered[-1]['y']
                best = min(range(len(group)),
                           key=lambda j: (group[j]['x'] - lx) ** 2 + (group[j]['y'] - ly) ** 2)
            ordered.append(group.pop(best))

    # --- Save output_fov.csv ---
    rows = []
    for f in ordered:
        rows.append({'x': f['x'], 'y': f['y'], 'comp_idx': json.dumps([int(x) for x in f['comp_idx']])})

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(data_folder, 'output_fov.csv'), index=True)

    return len(df)
