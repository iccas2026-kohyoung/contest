"""Shared helpers for per-solver runs (2_run.py, 3_view.py).

Both the solver (`solve()`) and the evaluator (`Checker(folder)`) hardcode
`output_fov.csv` at the dataset-folder root. To keep results separated by
solver, we run/evaluate at the root and then shuttle the generated artifacts
into a `<solver>/` subfolder so `simulation_data/` stays pristine and
re-runnable.

Layout produced:
    simulation_data/<dataset>/
        input_*.csv                # pristine inputs (never mutated)
        <solver>/
            output_fov.csv         # solver FOV plan
            result.html            # 3_view.py output
"""
import os
import shutil
from contextlib import contextmanager

OUTPUT_FOV = 'output_fov.csv'
ERROR_LOG = 'error.log'
RESULT_HTML = 'result.html'

SOLVER_DIR = {
    'ky': 'ky_solver',
    'greedy': 'greedy_solver',
}


def resolve_solver_dir(name):
    """Map shorthand solver names to their actual folder names."""
    return SOLVER_DIR.get(name, name)


def release_logger(checker):
    """Close the Checker's logging FileHandler so its error.log can be removed
    (Windows keeps the file locked while the handler is open)."""
    lg = getattr(checker, 'logger', None)
    if lg is not None:
        for h in list(lg.handlers):
            try:
                h.close()
            except Exception:
                pass
            lg.removeHandler(h)


def solver_subdir(dataset_path, solver):
    """Return (and create) the per-solver subfolder inside a dataset folder."""
    d = os.path.join(dataset_path, solver)
    os.makedirs(d, exist_ok=True)
    return d


def persist(dataset_path, solver):
    """After solve(): move output_fov.csv into <solver>/ and drop any stray error.log."""
    sub = solver_subdir(dataset_path, solver)

    out_root = os.path.join(dataset_path, OUTPUT_FOV)
    if os.path.isfile(out_root):
        shutil.move(out_root, os.path.join(sub, OUTPUT_FOV))

    err = os.path.join(dataset_path, ERROR_LOG)
    if os.path.isfile(err):
        os.remove(err)


@contextmanager
def stage(dataset_path, solver):
    """Temporarily place a solver's saved output_fov.csv at the dataset-folder
    root so Checker(dataset_path) reads it, then remove on exit.
    Used by `2_run.py --eval` and `3_view.py`."""
    sub = solver_subdir(dataset_path, solver)
    out_root = os.path.join(dataset_path, OUTPUT_FOV)

    saved_out = os.path.join(sub, OUTPUT_FOV)
    if not os.path.isfile(saved_out):
        raise FileNotFoundError(f"no saved result for solver '{solver}' at {saved_out}")

    shutil.copyfile(saved_out, out_root)
    try:
        yield dataset_path
    finally:
        if os.path.isfile(out_root):
            os.remove(out_root)
        err = os.path.join(dataset_path, ERROR_LOG)
        if os.path.isfile(err):
            os.remove(err)
