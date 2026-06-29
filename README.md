# ICCAS 2026 KohYoung AI Contest

**Resource-Aware AOI Computation Time Optimization**

Contest page: https://iccas2026-kohyoung.github.io/contest/

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the baseline solver

```bash
python 2_run.py --solver greedy
```

This runs the baseline greedy solver (`greedy_solver/solver.py`) on all datasets in `simulation_data/` and prints a result table:

```
  PCB | FOVs | Core | Cover | Order | CT (s)
-----------------------------------------------
  ... |  ... |  ... |  ...  |  ...  |  ...
-----------------------------------------------
  AVG |      |      |       |       |  XX.XX
```

- **FOVs**: number of FOV shots your solver produced
- **Core**: max parallel cores available
- **Cover**: whether all components are covered by FOVs (`True`/`False`)
- **Order**: whether FOV inspection order satisfies type constraints
- **CT (s)**: computation time (lower is better)

### 3. Run the reference solver (KohYoung)

```bash
python 2_run.py --solver ky
```

Each run is **kept separate per solver**: outputs are written to
`simulation_data/<dataset>/<solver>/` (so `ky` and `greedy` never overwrite each
other), and a grading table `summary_<solver>.csv` is written at the repo root.
The input files under each dataset folder are never modified.

### 4. View a result

```bash
python 3_view.py --solver ky --dataset S00_sparse_fast_001 --open
```

Renders `simulation_data/<dataset>/<solver>/result.html` — an interactive PCB
layout + timing gantt. Omit `--dataset` to render all datasets.

### 5. Re-score existing results (no re-solving)

```bash
python 2_run.py --solver ky --eval
```

---

## Project Structure

```
contest/
├── my_solver/                 # ★ START HERE — copy & rename to your team name
│   ├── __init__.py
│   └── solver.py
├── greedy_solver/             # Baseline solver (simple greedy)
│   ├── __init__.py
│   └── solver.py
├── ky_solver/                 # KohYoung solver (target to beat)
├── utils/
│   ├── checker.py             # Evaluation & scoring
│   └── generator.py           # Scenario data generator
├── simulation_data/           # 96 test datasets (8 scenarios x 12)
│   ├── S00_sparse_fast_001/
│   │   ├── input_component.csv
│   │   ├── input_size.csv
│   │   ├── input_parameter.csv
│   │   ├── input_step_region.csv
│   │   └── <solver>/          # per-solver results (e.g. ky/, greedy/)
│   │       ├── output_fov.csv     # <- the solver writes this
│   │       └── result.html        # <- 3_view.py renders this
│   └── ...
├── 1_generate_data.py         # Generate new scenario datasets
├── 2_run.py                   # Run a solver & score it (per solver)
├── 3_view.py                  # Render result.html for a solver
└── requirements.txt
```

---

## Data Format

### Input

Each dataset folder contains:

| File | Description |
|---|---|
| `input_component.csv` | Component positions (`tl_x, tl_y, br_x, br_y`), type, inspection time |
| `input_size.csv` | PCB dimensions and FOV size |
| `input_parameter.csv` | Capture time, reconstruction time, max cores, stage velocity/acceleration |

### Output

Your solver must write `output_fov.csv`:

| Column | Description |
|---|---|
| `x`, `y` | FOV center position |
| `comp_idx` | JSON list of component indices covered by this FOV |

---

## How to Write Your Solver

1. **Copy** the `my_solver/` folder and rename it to your team name (e.g. `team_alpha/`).
2. **Edit** `team_alpha/solver.py` — implement your logic in the `solve()` function.
3. **Run** your solver:

```bash
python 2_run.py --solver team_alpha
```

The function signature:

```python
def solve(data_folder: str) -> int:
    # Read inputs from data_folder
    # Compute FOV placements
    # Write output_fov.csv to data_folder
    # Return number of FOVs
```

### Constraints

- Every component must be fully contained within at least one FOV
- `side=0` (top) components use full FOV (`fov_w x fov_h`)
- `side=1` (side) components use half FOV (`fov_w/2 x fov_h/2`), centered at the same point
- Components exceeding their effective FOV size must be covered by multiple FOVs (tiling)
- FOVs must be ordered by component type (descending): Fiducial(2) > Barcode(1) > Normal(0)
- Fiducial components (`type=2`) require a dedicated FOV each
- See `ICCAS_2026_CONTEST_RULES.html` for full rules

---

## Evaluation

- **Practice data** (96 datasets): included in `simulation_data/` for development and testing
- **Final test data**: a separate hidden test set will be used for official scoring. The test data will be released via this repository after the contest ends.

---

## Contact

For questions, contact: yh.yoo@kohyoung.com

