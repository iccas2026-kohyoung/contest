import os
import random
import numpy as np
from rtree import index

class Generator():
    def __init__(self):
        self.components = []

    def initialize(self, pcb_size, n_components, component_info, big_component_info):
        self.pcb_height = pcb_size['height']
        self.pcb_width = pcb_size['width']
        self.n_components = n_components
        self.component_info = component_info
        self.big_component_info = big_component_info
        self.components = []

    def biased_size(self, min_size, max_size, power=2.0):
        r = random.random() ** power
        return round(min_size + (max_size - min_size) * r, 2)

    def set_parameter(self, capture_time, recon_time, side_capture_time, max_core,
                       v_x=1000, v_y=1000, a_x=9800, a_y=9800):
        self.parameter = {
            'capture_time': capture_time,
            'recon_time': recon_time,
            'side_capture_time': side_capture_time,
            'max_core': max_core,
            'v_x': v_x,
            'v_y': v_y,
            'a_x': a_x,
            'a_y': a_y
        }

    def set_size_info(self, pcb_size, fov_size):
        self.pcb_size = pcb_size
        if isinstance(fov_size, (list, tuple)):
            self.fov_x, self.fov_y = fov_size
        else:
            self.fov_x = self.fov_y = fov_size

    def generate_step_regions(self, n_regions=None, size_ratio=(0.2, 0.33)):
        if n_regions is None:
            n_regions = random.randint(1, 2)
        self.step_regions = []
        for _ in range(n_regions):
            w = self.pcb_width * random.uniform(size_ratio[0], size_ratio[1])
            h = self.pcb_height * random.uniform(size_ratio[0], size_ratio[1])
            tl_x = random.uniform(0, self.pcb_width - w)
            tl_y = random.uniform(0, self.pcb_height - h)
            self.step_regions.append([round(tl_x, 2), round(tl_y, 2), round(tl_x + w, 2), round(tl_y + h, 2)])

    def _get_step(self, tl_x, tl_y, br_x, br_y):
        if not hasattr(self, 'step_regions'):
            return 0
        for r in self.step_regions:
            if tl_x < r[2] and br_x > r[0] and tl_y < r[3] and br_y > r[1]:
                return 1
        return 0

    def generate_fiducials(self, max_offset=10):
        size = 5
        diagonal_points = ["top-left", "bottom-right", "top-right", "bottom-left"]
        corner = random.choice(diagonal_points)

        corner_base = {
            "top-left": (max_offset, max_offset),
            "top-right": (self.pcb_width - size - max_offset, max_offset),
            "bottom-left": (max_offset, self.pcb_height - size - max_offset),
            "bottom-right": (self.pcb_height - size - max_offset, self.pcb_height - size - max_offset),
        }

        fiducials = []
        while True:
            base_x, base_y = corner_base[corner]
            offset_x = random.randint(-max_offset, max_offset)
            offset_y = random.randint(-max_offset, max_offset)
            tl_x = min(max(base_x + offset_x, 0), self.pcb_width - size)
            tl_y = min(max(base_y + offset_y, 0), self.pcb_height - size)
            br_x = tl_x + size
            br_y = tl_y + size

            overlap = False
            for comp in self.components:
                if not (br_x <= comp[1] or tl_x >= comp[3] or br_y <= comp[2] or tl_y >= comp[4]):
                    overlap = True
                    break

            if not overlap:
                step = self._get_step(tl_x, tl_y, br_x, br_y)
                fiducials.append([tl_x, tl_y, br_x, br_y, 2, 0, step, round(size*size/100., 3)])
                break


        self.components = fiducials + self.components

    def generate_usermarks(self, n_usermarks=None, max_attempts=200):
        if n_usermarks is None:
            n_usermarks = random.randint(0, 4)
        if n_usermarks == 0:
            return

        usermarks = []
        for _ in range(n_usermarks):
            for _attempt in range(max_attempts):
                min_size, max_size = self.component_info['size']
                w = self.biased_size(min_size, max_size)
                h = self.biased_size(min_size, max_size)
                tl_x = random.uniform(0, self.pcb_width - w)
                tl_y = random.uniform(0, self.pcb_height - h)
                br_x = tl_x + w
                br_y = tl_y + h

                overlap = False
                for comp in self.components + usermarks:
                    if not (br_x <= comp[1] or tl_x >= comp[3] or br_y <= comp[2] or tl_y >= comp[4]):
                        overlap = True
                        break

                if not overlap:
                    step = self._get_step(tl_x, tl_y, br_x, br_y)
                    usermarks.append([tl_x, tl_y, br_x, br_y, 1, 0, step, round(w * h / 100., 3)])
                    break

        fiducial_count = sum(1 for c in self.components if c[4] == 2)
        self.components = self.components[:fiducial_count] + usermarks + self.components[fiducial_count:]

    def _make_component(self, tl_x, tl_y, w, h, side_ratio, side_fov_limit):
        br_x = tl_x + w
        br_y = tl_y + h
        if br_x > self.pcb_width or br_y > self.pcb_height:
            return None
        side = 1 if random.random() < side_ratio else 0
        step = self._get_step(tl_x, tl_y, br_x, br_y)
        return [tl_x, tl_y, br_x, br_y, 0, side, step, round((w * h + 0.3 * h) / 100., 3)]

    def _sample_std_size(self):
        STD_SIZES = [
            (1.0, 0.5), (1.6, 0.8), (2.0, 1.25), (3.2, 1.6),
            (3.2, 2.5), (4.5, 3.2), (5.7, 5.0), (8.0, 6.5),
        ]
        w, h = random.choice(STD_SIZES)
        if random.random() < 0.5:
            w, h = h, w
        w += random.uniform(-0.1, 0.1)
        h += random.uniform(-0.1, 0.1)
        return round(max(w, 0.5), 2), round(max(h, 0.5), 2)

    def generate_components(self, grid_resolution=10.0, cluster_count=[10, 30],
                            n_component_per_cluster=[20, 30], cluster_radius=[10., 50.],
                            bernoulli_prob=0.3, side_ratio=0.2,
                            fov_size=50, use_std_sizes=True, density_bias=0.0,
                            n_dead_zones=0, n_ic_centers=0):

        components = []
        grid_x = int(self.pcb_width / grid_resolution)
        grid_y = int(self.pcb_height / grid_resolution)

        fov_limit = fov_size - 1
        side_fov_limit = fov_size / 2.0 - 1

        dead_zones = []
        for _ in range(n_dead_zones):
            dw = random.uniform(30, 80)
            dh = random.uniform(30, 80)
            dx = random.uniform(0, self.pcb_width - dw)
            dy = random.uniform(0, self.pcb_height - dh)
            dead_zones.append((dx, dy, dx + dw, dy + dh))

        pcb_cx = self.pcb_width / 2.0
        pcb_cy = self.pcb_height / 2.0
        max_dist = ((pcb_cx ** 2) + (pcb_cy ** 2)) ** 0.5

        for gx in range(grid_x):
            for gy in range(grid_y):
                cx = (gx + 0.5) * grid_resolution
                cy = (gy + 0.5) * grid_resolution

                in_dead = False
                for dz in dead_zones:
                    if dz[0] <= cx <= dz[2] and dz[1] <= cy <= dz[3]:
                        in_dead = True
                        break
                if in_dead:
                    continue

                prob = bernoulli_prob
                if density_bias != 0.0:
                    dist = ((cx - pcb_cx) ** 2 + (cy - pcb_cy) ** 2) ** 0.5 / max_dist
                    if density_bias > 0:
                        prob *= (1.0 + density_bias * (1.0 - dist))
                    else:
                        prob *= (1.0 - density_bias * dist)
                    prob = min(prob, 0.9)

                if random.random() > prob:
                    continue

                tl_x = gx * grid_resolution + random.uniform(0.05, 0.95)
                tl_y = gy * grid_resolution + random.uniform(0.05, 0.95)

                if random.random() < self.big_component_info['ratio']:
                    min_size, max_size = self.big_component_info['size']
                    w = self.biased_size(min_size, max_size)
                    h = self.biased_size(min_size, max_size)
                    r = random.random()
                    if r < 0.25:
                        w *= 0.5
                    elif r < 0.5:
                        h *= 0.5
                elif use_std_sizes and random.random() < 0.7:
                    w, h = self._sample_std_size()
                else:
                    min_size, max_size = self.component_info['size']
                    w = self.biased_size(min_size, max_size)
                    h = self.biased_size(min_size, max_size)

                comp = self._make_component(tl_x, tl_y, w, h, side_ratio, side_fov_limit)
                if comp:
                    components.append(comp)

        for _ in range(n_ic_centers):
            ic_w = random.uniform(20, 50)
            ic_h = random.uniform(20, 50)
            ic_x = random.uniform(ic_w, self.pcb_width - ic_w)
            ic_y = random.uniform(ic_h, self.pcb_height - ic_h)
            components.append([ic_x - ic_w / 2, ic_y - ic_h / 2,
                               ic_x + ic_w / 2, ic_y + ic_h / 2,
                               0, 0, self._get_step(ic_x - ic_w / 2, ic_y - ic_h / 2,
                                                    ic_x + ic_w / 2, ic_y + ic_h / 2),
                               round((ic_w * ic_h + 0.3 * ic_h) / 100., 3)])

            n_pins = random.randint(30, 80)
            ring_margin = random.uniform(2, 5)
            for _ in range(n_pins):
                edge = random.randint(0, 3)
                if edge == 0:
                    px = ic_x + random.uniform(-ic_w / 2 - ring_margin, ic_w / 2 + ring_margin)
                    py = ic_y - ic_h / 2 - ring_margin + random.uniform(-1, 1)
                elif edge == 1:
                    px = ic_x + random.uniform(-ic_w / 2 - ring_margin, ic_w / 2 + ring_margin)
                    py = ic_y + ic_h / 2 + ring_margin + random.uniform(-1, 1)
                elif edge == 2:
                    px = ic_x - ic_w / 2 - ring_margin + random.uniform(-1, 1)
                    py = ic_y + random.uniform(-ic_h / 2 - ring_margin, ic_h / 2 + ring_margin)
                else:
                    px = ic_x + ic_w / 2 + ring_margin + random.uniform(-1, 1)
                    py = ic_y + random.uniform(-ic_h / 2 - ring_margin, ic_h / 2 + ring_margin)

                if use_std_sizes:
                    w, h = self._sample_std_size()
                else:
                    w = self.biased_size(*self.component_info['size'])
                    h = self.biased_size(*self.component_info['size'])

                tl_x = max(0, px - w / 2)
                tl_y = max(0, py - h / 2)
                comp = self._make_component(tl_x, tl_y, w, h, side_ratio, side_fov_limit)
                if comp:
                    components.append(comp)

        clustered_components = components.copy()
        random.shuffle(clustered_components)

        for base in clustered_components[:random.randint(cluster_count[0], cluster_count[1])]:
            base_tl_x, base_tl_y, base_br_x, base_br_y, types, _side, _step, time = base
            center_x = (base_tl_x + base_br_x) / 2.0
            center_y = (base_tl_y + base_br_y) / 2.0

            for _ in range(random.randint(n_component_per_cluster[0], n_component_per_cluster[1])):
                radius = random.uniform(cluster_radius[0], cluster_radius[1])
                offset_x = random.uniform(-radius, radius)
                offset_y = random.uniform(-radius, radius)

                if use_std_sizes and random.random() < 0.7:
                    w, h = self._sample_std_size()
                else:
                    c_min_size, c_max_size = self.component_info['size']
                    w = self.biased_size(c_min_size, c_max_size)
                    h = self.biased_size(c_min_size, c_max_size)

                tl_x = min(max(center_x + offset_x, 0), self.pcb_width - w)
                tl_y = min(max(center_y + offset_y, 0), self.pcb_height - h)

                comp = self._make_component(tl_x, tl_y, w, h, side_ratio, side_fov_limit)
                if comp:
                    components.append(comp)

        final_components = []
        random.shuffle(components)
        idx = index.Index()

        for i, c in enumerate(components):
            tl_x, tl_y, br_x, br_y = c[0], c[1], c[2], c[3]
            hits = list(idx.intersection((tl_x, tl_y, br_x, br_y)))
            if not hits:
                final_components.append(c)
                idx.insert(i, (tl_x, tl_y, br_x, br_y))

        self.components = final_components[:self.n_components]

    def generate_grid_components(self, spacing=6.0, comp_w=3.2, comp_h=1.6, jitter=0.1,
                                  side_ratio=0.2, fov_size=50):
        side_fov_limit = fov_size / 2.0 - 1
        components = []
        margin = 5.0
        x = margin
        while x + comp_w <= self.pcb_width - margin:
            y = margin
            while y + comp_h <= self.pcb_height - margin:
                w = comp_w + random.uniform(-jitter, jitter)
                h = comp_h + random.uniform(-jitter, jitter)
                tl_x = x + random.uniform(-jitter, jitter)
                tl_y = y + random.uniform(-jitter, jitter)
                tl_x = max(0, min(tl_x, self.pcb_width - w))
                tl_y = max(0, min(tl_y, self.pcb_height - h))
                comp = self._make_component(tl_x, tl_y, w, h, side_ratio, side_fov_limit)
                if comp:
                    components.append(comp)
                y += spacing
            x += spacing
        random.shuffle(components)
        self.components = components[:self.n_components]

    def add_component(self, tl_x, tl_y, br_x, br_y, types, side, step, time):
        self.components.append([tl_x, tl_y, br_x, br_y, types, side, step, time])

    def save_job_info(self, folder):
        os.makedirs(folder, exist_ok=True)
        # component info
        component_file = folder + '/input_component.csv'
        with open(component_file, mode='w', newline='') as f:
            f.write(",tl_x,tl_y,br_x,br_y,type,side,step,time\n")

            for idx, row in enumerate(self.components):
                # tl_x, tl_y, br_x, br_y, type, side, step, time
                f.write(f"{idx},{row[0]:.2f},{row[1]:.2f},{row[2]:.2f},{row[3]:.2f},{row[4]},{row[5]},{row[6]},{row[7]}\n")

        # size info
        size_file = folder + '/input_size.csv'
        with open(size_file, mode='w', newline='') as f:
            f.write("axis,pcb_size,fov_size\n")
            f.write(f"x,{self.pcb_size['width']},{self.fov_x}\n")
            f.write(f"y,{self.pcb_size['height']},{self.fov_y}\n")

        # step region info
        if hasattr(self, 'step_regions') and self.step_regions:
            step_file = folder + '/input_step_region.csv'
            with open(step_file, mode='w', newline='') as f:
                f.write(",tl_x,tl_y,br_x,br_y\n")
                for idx, r in enumerate(self.step_regions):
                    f.write(f"{idx},{r[0]},{r[1]},{r[2]},{r[3]}\n")

        # parameter info
        param_file = folder + '/input_parameter.csv'
        with open(param_file, mode='w', newline='') as f:
            f.write("capture_time,recon_time,side_capture_time,max_core,v_x,v_y,a_x,a_y\n")
            f.write(f"{self.parameter['capture_time']},{self.parameter['recon_time']},{self.parameter['side_capture_time']},{self.parameter['max_core']},"
                    f"{self.parameter['v_x']},{self.parameter['v_y']},{self.parameter['a_x']},{self.parameter['a_y']}\n")
