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
- **Evaluation data** (96 datasets): released in `evaluation_data/` — used for official scoring

---

## Results

Evaluated on **96 datasets** (8 categories × 12) · Deadline: 2026-10-09

**Scoring:** `Total = ΣCT + ΣRT × α + Σk × β` (α = 1, β = 10)

### Full Solver Rankings

| # | Team | ΣCT | ΣRT | Σk×10 | Total |
|---|------|----:|----:|------:|------:|
| 🥇 | UOS-OPT | 7,625.6 | 33.4 | 5,650 | **13,309.0** |
| 🥈 | SPAC | 7,587.1 | 33.4 | 5,690 | **13,310.5** |
| 🥉 | ARGOS | 7,668.8 | 42.4 | 5,640 | **13,351.1** |
| 4 | DblCheese | 7,667.7 | 55.8 | 5,660 | **13,383.5** |
| 5 | UOS_AOI | 7,638.2 | 87.8 | 5,660 | **13,386.0** |
| 6 | 4D-REPUBLIC | 7,702.7 | 33.8 | 5,650 | **13,386.5** |
| 7 | RML | 7,965.6 | 37.1 | 5,510 | **13,512.7** |
| 8 | KOFAM | 7,921.8 | 46.1 | 5,560 | **13,527.9** |
| 9 | RLDR | 7,995.8 | 57.1 | 5,550 | **13,602.9** |
| 10 | Auto-farming | 7,969.2 | 235.3 | 5,550 | **13,754.6** |
| 11 | Optima | 8,420.1 | 150.5 | 5,510 | **14,080.6** |
| 12 | IRSL | 8,716.9 | 25.7 | 5,360 | **14,102.6** |
| 13 | Kohyoung ◆ | 8,539.2 | 147.8 | 5,430 | **14,117.0** |

### Routing Only — FOV Path Optimization

FOV positions fixed from Kohyoung baseline. Each team's router reorders for minimum CT.

| # | Team | ΣCT | vs Kohyoung |
|---|------|----:|-------------|
| 🥇 | UOS-OPT | 8,502.8 | −36.3 (−0.4%) |
| 🥈 | Kohyoung ◆ | 8,539.2 | — |
| 🥉 | DblCheese | 8,711.2 | +172.1 (+2.0%) |
| 4 | UOS_AOI | 8,773.9 | +234.8 (+2.7%) |
| 5 | RLDR | 8,786.9 | +247.7 (+2.9%) |
| 6 | SPAC | 8,807.9 | +268.8 (+3.1%) |
| 7 | RML | 8,812.0 | +272.9 (+3.2%) |
| 8 | KOFAM | 8,824.8 | +285.6 (+3.3%) |
| 9 | Auto-farming | 8,898.9 | +359.7 (+4.2%) |
| 10 | ARGOS | 8,873.2 | +334.1 (+3.9%) |
| 11 | 4D-REPUBLIC | 8,914.1 | +375.0 (+4.4%) |
| 12 | IRSL | 8,929.4 | +390.3 (+4.6%) |
| 13 | Optima | 8,911.1 | +371.9 (+4.4%) |

◆ Kohyoung = baseline solver

Evaluation datasets and individual results have been distributed to each team's repository.

---

## Contact

For questions, contact: yh.yoo@kohyoung.com

