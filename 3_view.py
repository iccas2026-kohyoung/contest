"""Render the interactive result viewer (result.html) for a solver's saved output.

Reads each dataset's `<solver>/output_fov.csv` (produced by `2_run.py --solver <name>`)
and writes `<dataset>/<solver>/result.html` — an interactive PCB layout + timing gantt.
"""
import os
import shutil
import argparse
import logging
import webbrowser
logging.disable(logging.CRITICAL)

from utils.checker import Checker
import run_utils


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Render result.html for a solver (per solver).')
    parser.add_argument('--data', default='simulation_data', help='Data folder (default: simulation_data)')
    parser.add_argument('--solver', default='ky', help='Which solver\'s saved result to view (e.g. ky, greedy, team_alpha)')
    parser.add_argument('--dataset', default=None, help='Render a single dataset (folder name); default: all')
    parser.add_argument('--open', action='store_true', help='Open the first rendered result.html in a browser')
    args = parser.parse_args()

    solver_dir = run_utils.resolve_solver_dir(args.solver)
    root = args.data
    if args.dataset:
        folders = [args.dataset]
    else:
        folders = sorted([f for f in os.listdir(root) if os.path.isdir(os.path.join(root, f))])

    rendered = []
    missing = []
    for folder in folders:
        path = os.path.join(root, folder)
        sub = os.path.join(path, solver_dir)
        if not os.path.isfile(os.path.join(sub, run_utils.OUTPUT_FOV)):
            missing.append(folder)
            continue
        with run_utils.stage(path, solver_dir):
            c = Checker(path)
            cover = c.cover_all_components()
            order = c.fov_inspection_order()
            if not cover or not order:
                c.penalty_solver()
            c.save_combined_view()  # writes <path>/result.html
            run_utils.release_logger(c)
            src = os.path.join(path, run_utils.RESULT_HTML)
            dst = os.path.join(sub, run_utils.RESULT_HTML)
            if os.path.isfile(src):
                shutil.move(src, dst)
                rendered.append(dst)

    for r in rendered:
        print(f'rendered: {r}')
    if missing:
        print(f'\nskipped {len(missing)} dataset(s) with no {solver_dir}/ output '
              f'(run: python 2_run.py --solver {args.solver})')
        if not args.dataset:
            print('  e.g. ' + ', '.join(missing[:5]) + ('...' if len(missing) > 5 else ''))

    if args.open and rendered:
        webbrowser.open('file://' + os.path.abspath(rendered[0]))
