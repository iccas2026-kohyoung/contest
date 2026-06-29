"""
Solver template for ICCAS 2026 KohYoung AI Contest.

Rename the folder 'my_solver' to your team name (e.g. 'team_alpha').
Implement your solver logic in the solve() function below.

Usage:
    python 2_run.py --solver my_solver
    python 2_run.py --solver team_alpha   (after renaming)

Input files (in data_folder):
    input_component.csv  — columns: tl_x, tl_y, br_x, br_y, type, side, step, weight
    input_size.csv       — columns: fov_size, pcb_size

Output:
    Write output_fov.csv to data_folder with columns: x, y, comp_idx
    Return the number of FOVs (int).

Rules:
    - Each component must be fully covered by at least one FOV.
    - side=0 (top) components use full FOV (fov_w x fov_h).
    - side=1 (side) components use half FOV (fov_w/2 x fov_h/2), centered at the same point.
    - FOV inspection order must be non-increasing by type (Fiducial=2 > Barcode=1 > Normal=0).
    - comp_idx is a JSON list of component indices covered by each FOV.
    - See ICCAS_2026_CONTEST_RULES.html for full details.
"""
import os
import json
import numpy as np
import pandas as pd


def solve(data_folder: str) -> int:
    comp = pd.read_csv(os.path.join(data_folder, 'input_component.csv'))
    size = pd.read_csv(os.path.join(data_folder, 'input_size.csv'))

    fov_w = float(size['fov_size'].iloc[0])
    fov_h = float(size['fov_size'].iloc[1])
    pcb_w = float(size['pcb_size'].iloc[0])
    pcb_h = float(size['pcb_size'].iloc[1])
    side_fov_w = fov_w / 2.0
    side_fov_h = fov_h / 2.0

    n = len(comp)
    comp_cx = ((comp['tl_x'] + comp['br_x']) / 2.0).values
    comp_cy = ((comp['tl_y'] + comp['br_y']) / 2.0).values
    comp_w = (comp['br_x'] - comp['tl_x']).values
    comp_h = (comp['br_y'] - comp['tl_y']).values
    comp_side = comp['side'].astype(int).values if 'side' in comp.columns else np.zeros(n, dtype=int)
    comp_step = comp['step'].astype(int).values if 'step' in comp.columns else np.zeros(n, dtype=int)
    comp_type = comp['type'].astype(int).values

    # TODO: implement your solver here
    # This template places one FOV per component at its center (naive baseline).

    fovs = []
    for i in range(n):
        fovs.append({
            'x': comp_cx[i],
            'y': comp_cy[i],
            'comp_idx': [i],
            'type': int(comp_type[i]),
            'step': int(comp_step[i]),
        })

    # Sort by type descending (Fiducial=2 > Barcode=1 > Normal=0)
    fovs.sort(key=lambda f: -f['type'])

    # Write output_fov.csv
    rows = []
    for f in fovs:
        rows.append({
            'x': f['x'],
            'y': f['y'],
            'comp_idx': json.dumps([int(x) for x in f['comp_idx']]),
        })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(data_folder, 'output_fov.csv'), index=True)

    return len(df)
