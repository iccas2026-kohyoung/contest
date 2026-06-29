import os
import time
import argparse
import logging
import csv
import pandas as pd
logging.disable(logging.CRITICAL)

from utils.checker import Checker
import run_utils

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run a solver on all PCBs and score the results (per solver).')
    parser.add_argument('--data', default='simulation_data', help='Data folder containing PCB subdirectories (default: simulation_data)')
    parser.add_argument('--solver', default='ky', help='Solver to use: ky, greedy, or your team folder name (e.g. my_solver)')
    parser.add_argument('--eval', action='store_true', help='Evaluation only: skip solving and score existing <solver>/ outputs')
    args = parser.parse_args()

    solver_dir = run_utils.resolve_solver_dir(args.solver)

    if not args.eval:
        if args.solver == 'ky':
            from ky_solver._solver import solve
        else:
            import importlib
            solver_mod = importlib.import_module(solver_dir)
            solve = solver_mod.solve

    B = '\033[94m'; R = '\033[91m'; G = '\033[92m'; D = '\033[90m'; RST = '\033[0m'

    root = args.data
    folders = sorted([f for f in os.listdir(root) if os.path.isdir(os.path.join(root, f))])
    W = max(len(f) for f in folders) if folders else 10
    sep = D + '-' * (W + 66) + RST

    print(f'{B}{"PCB":>{W}} | {"Comps":>6} | {"FOVs":>5} | {"Core":>5} | {"Cover":>6} | {"Order":>6} | {"Cycle Time":>11} | {"Calc Time":>10}{RST}  (solver: {args.solver})')
    print(sep)

    total_ct = 0.0
    total_solve = 0.0
    n_penalty = 0
    rows = []
    prev_type = None

    for folder in folders:
        cur_type = '_'.join(folder.split('_')[:-1])
        if prev_type is not None and cur_type != prev_type:
            print(sep)
        prev_type = cur_type
        path = os.path.join(root, folder)

        if not args.eval:
            # solve at folder root, then shuttle artifacts into <solver>/
            t0 = time.perf_counter()
            n = solve(path)
            solve_time = time.perf_counter() - t0
            c = Checker(path)
            cover = c.cover_all_components()
            order = c.fov_inspection_order()
            penalty = not cover or not order
            if penalty:
                c.penalty_solver()
                n_penalty += 1
                cover_after = not any(c.component.get('error', 0)) if 'error' in c.component.columns else True
                order_after = all(c.fov['type'].iloc[i] >= c.fov['type'].iloc[i+1] for i in range(len(c.fov)-1))
            else:
                cover_after, order_after = cover, order
            ct = c.compute_ct()
            core = getattr(c, '_optimal_core', int(c.parameter['max_core'].iloc[0]))
            n_comp = len(c.component)
            run_utils.release_logger(c)
            run_utils.persist(path, solver_dir)
        else:
            # score existing saved result
            with run_utils.stage(path, solver_dir):
                c = Checker(path)
                cover = c.cover_all_components()
                order = c.fov_inspection_order()
                penalty = not cover or not order
                if penalty:
                    c.penalty_solver()
                    n_penalty += 1
                    cover_after = not any(c.component.get('error', 0)) if 'error' in c.component.columns else True
                    order_after = all(c.fov['type'].iloc[i] >= c.fov['type'].iloc[i+1] for i in range(len(c.fov)-1))
                else:
                    cover_after, order_after = cover, order
                n = len(c.fov)
                ct = c.compute_ct()
                core = getattr(c, '_optimal_core', int(c.parameter['max_core'].iloc[0]))
                n_comp = len(c.component)
                run_utils.release_logger(c)
            solve_time = 0.0

        total_ct += ct
        total_solve += solve_time
        p = '*' if penalty else ''
        cov_color = R if not cover_after else G
        ct_color = R if penalty else ''
        ct_rst = RST if penalty else ''
        print(f'{folder:>{W}} | {n_comp:>6} | {n:>5} | {core:>5d} | {cov_color}{str(cover_after):>6}{RST} | {str(order_after):>6} | {ct_color}{ct:>10.2f}{p}{ct_rst} | {solve_time:>9.2f}')
        rows.append({'dataset': folder, 'n_comp': n_comp, 'n_fov': n, 'core': core,
                     'cover': bool(cover_after), 'order': bool(order_after),
                     'ct': round(float(ct), 2), 'solve_s': round(solve_time, 2)})

    print(sep)
    N = len(folders) if folders else 1
    avg_ct = total_ct / N
    print(f'{"AVG":>{W}} | {"":>6} | {"":>5} | {"":>5} | {"":>6} | {"":>6} | {avg_ct:>10.2f} | {total_solve / N:>9.2f}')
    if n_penalty > 0:
        print(f'\n{R}* = penalty_solver applied ({n_penalty}/{len(folders)} datasets){RST}')

    # per-solver grading summary
    summary_path = f'summary_{args.solver}.csv'
    with open(summary_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['dataset', 'n_comp', 'n_fov', 'core', 'cover', 'order', 'ct', 'solve_s'])
        w.writeheader()
        w.writerows(rows)
    print(f'\nSaved {summary_path}  (AVG CT {avg_ct:.2f}s over {len(folders)} datasets)')
