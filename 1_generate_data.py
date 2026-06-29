import random
import os
import shutil
import hashlib
from utils.generator import Generator

SCENARIOS = {
    'S00_sparse_fast': {'layout': 'sparse', 'recon': 'fast'},
    'S01_sparse_slow': {'layout': 'sparse', 'recon': 'slow'},
    'S02_dense_fast':  {'layout': 'dense',  'recon': 'fast'},
    'S03_dense_slow':  {'layout': 'dense',  'recon': 'slow'},
    'S04_grid_fast':   {'layout': 'grid',   'recon': 'fast'},
    'S05_grid_slow':   {'layout': 'grid',   'recon': 'slow'},
    'S06_big_fast':    {'layout': 'big',    'recon': 'fast'},
    'S07_big_slow':    {'layout': 'big',    'recon': 'slow'},
}

N_PER_TYPE = 12
PCB_MIN, PCB_MAX = 128, 512
FOV_MIN, FOV_MAX = 50, 100


def generate_one(scenario, seed):
    random.seed(seed)
    cfg = SCENARIOS[scenario]
    layout = cfg['layout']
    recon_time = 0.5 if cfg['recon'] == 'fast' else 1.3

    pcb_w = random.randint(PCB_MIN, PCB_MAX)
    pcb_h = random.randint(PCB_MIN, PCB_MAX)
    pcb_size = {'width': pcb_w, 'height': pcb_h}
    fov_x = random.randint(FOV_MIN, FOV_MAX)
    fov_y = random.randint(FOV_MIN, FOV_MAX)
    fov_min = min(fov_x, fov_y)
    g = Generator()

    if layout == 'sparse':
        n_comp = random.randint(800, 1200)
        big_info = {'size': [40, 60], 'ratio': random.uniform(0.05, 0.15)}
        comp_info = {'size': [1, 15], 'ratio': 1}
        g.initialize(pcb_size, n_comp, comp_info, big_info)
        g.generate_step_regions()
        g.generate_components(
            side_ratio=0.2, fov_size=fov_min,
            use_std_sizes=True, density_bias=random.uniform(-0.5, 0.5),
            n_dead_zones=random.randint(0, 3), n_ic_centers=random.randint(1, 4),
            bernoulli_prob=0.3, grid_resolution=10.0,
        )

    elif layout == 'dense':
        n_comp = random.randint(1600, 2400)
        big_info = {'size': [40, 60], 'ratio': random.uniform(0.05, 0.15)}
        comp_info = {'size': [1, 15], 'ratio': 1}
        g.initialize(pcb_size, n_comp, comp_info, big_info)
        g.generate_step_regions()
        g.generate_components(
            side_ratio=0.2, fov_size=fov_min,
            use_std_sizes=True, density_bias=random.uniform(-0.5, 0.5),
            n_dead_zones=random.randint(0, 1), n_ic_centers=random.randint(2, 6),
            bernoulli_prob=random.uniform(0.6, 0.8),
            grid_resolution=random.uniform(5.0, 7.0),
        )

    elif layout == 'grid':
        n_comp = random.randint(2000, 3000)
        comp_info = {'size': [1, 15], 'ratio': 1}
        big_info = {'size': [40, 60], 'ratio': 0}
        g.initialize(pcb_size, n_comp, comp_info, big_info)
        g.generate_step_regions()
        spacing = random.uniform(5.0, 8.0)
        g.generate_grid_components(
            spacing=spacing, comp_w=3.2, comp_h=1.6, jitter=0.1,
            side_ratio=0.2, fov_size=fov_min,
        )

    elif layout == 'big':
        n_comp = random.randint(600, 1000)
        big_info = {'size': [40, 80], 'ratio': random.uniform(0.4, 0.6)}
        comp_info = {'size': [1, 15], 'ratio': 1}
        g.initialize(pcb_size, n_comp, comp_info, big_info)
        g.generate_step_regions()
        g.generate_components(
            side_ratio=0.2, fov_size=fov_min,
            use_std_sizes=True, density_bias=random.uniform(-0.5, 0.5),
            n_dead_zones=random.randint(0, 3), n_ic_centers=random.randint(1, 4),
            bernoulli_prob=0.3, grid_resolution=10.0,
        )

    g.generate_fiducials()
    g.generate_usermarks()

    max_core = random.randint(4, 16)
    v_x = random.randint(200, 1000)
    v_y = random.randint(200, 1000)
    a_x = random.randint(4900, 9800)
    a_y = random.randint(4900, 9800)
    g.set_size_info(pcb_size, (fov_x, fov_y))
    g.set_parameter(
        capture_time=0.5,
        recon_time=recon_time,
        side_capture_time=0.75,
        max_core=max_core,
        v_x=v_x, v_y=v_y, a_x=a_x, a_y=a_y,
    )
    return g


if __name__ == '__main__':
    root = 'simulation_data'

    # remove old S*_ folders
    if os.path.exists(root):
        for d in os.listdir(root):
            if d.startswith('S0') and os.path.isdir(os.path.join(root, d)):
                shutil.rmtree(os.path.join(root, d))

    seed_base = 42
    for scenario in sorted(SCENARIOS.keys()):
        for i in range(N_PER_TYPE):
            seed = seed_base + int(hashlib.sha256(scenario.encode()).hexdigest(), 16) % (10**8) + i
            g = generate_one(scenario, seed)
            folder = f'{root}/{scenario}_{i+1:03d}'
            g.save_job_info(folder)
            n = len(g.components)
            print(f'{folder}: {n} components')

    print(f'\nGenerated {len(SCENARIOS) * N_PER_TYPE} datasets.')
