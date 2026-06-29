import os
import json
import math
import logging
import numpy as np
import pandas as pd

class Checker:
    def __init__(self, folder): 

        self.folder = folder 

        # log information
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{folder}")
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(f"[{self.folder}] %(message)s")

        if os.path.exists(os.path.join(self.folder, 'error.log')): 
            os.remove(os.path.join(self.folder, 'error.log'))
        file_handler = logging.FileHandler(os.path.join(self.folder, 'error.log'))
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

        # check files and load 
        component_file = os.path.join(folder, 'input_component.csv')
        if not os.path.isfile(component_file): 
            assert False, f'No component.csv file at {component_file}'

        size_file = os.path.join(folder, 'input_size.csv')
        if not os.path.isfile(size_file): 
            assert False, f'No size.csv file at {size_file}' 

        parameter_file = os.path.join(self.folder, 'input_parameter.csv') 
        if not os.path.isfile(parameter_file): 
            assert False, f'No parameter.csv file at {parameter_file}' 

        fov_file = os.path.join(folder, 'output_fov.csv') 
        if not os.path.isfile(fov_file): 
            assert False, f'No fov.csv file at {fov_file}' 

        self.component = pd.read_csv(component_file) 
        self.parameter = pd.read_csv(parameter_file) 
        size = pd.read_csv(size_file) 

        self.pcb_width = size['pcb_size'].iloc[0] 
        self.pcb_height = size['pcb_size'].iloc[1] 

        fov_size = size['fov_size'] 
        self.fov_width = fov_size.iloc[0]
        self.fov_height = fov_size.iloc[1]

        self.fov = pd.read_csv(fov_file)

        step_region_file = os.path.join(folder, 'input_step_region.csv')
        if os.path.isfile(step_region_file):
            self.step_regions = pd.read_csv(step_region_file)
        else:
            self.step_regions = pd.DataFrame(columns=['tl_x', 'tl_y', 'br_x', 'br_y'])

        # get fov rect 
        self.fov['tl_x'] = self.fov['x'] - self.fov_width / 2
        self.fov['tl_y'] = self.fov['y'] - self.fov_height / 2
        self.fov['br_x'] = self.fov['x'] + self.fov_width / 2
        self.fov['br_y'] = self.fov['y'] + self.fov_height / 2

        # update fov type 
        fov_type = [] 
        for i, fov in self.fov.iterrows(): 
            comp_idx = json.loads(self.fov.iloc[i]['comp_idx'])
            max_type = 0 
            for idx in comp_idx: 
                if idx < len(self.component):
                    max_type = max(max_type, self.component.iloc[idx]['type']) 

            fov_type.append(max_type) 

        self.fov['type'] = fov_type 

    def is_target_fully_covered(self, rects, target): # rect: fov, target: component
        tol = 1e-5
        tx1, ty1, tx2, ty2 = target

        # Step 1: Filter rectangles that intersect the target area
        filtered = []
        x_edges = {tx1, tx2}
        y_edges = {ty1, ty2}

        for _, x1, y1, x2, y2 in rects:
            if x2 <= tx1 - tol or x1 >= tx2 + tol or y2 <= ty1 - tol or y1 >= ty2 + tol:
                continue
            cx1, cy1 = max(x1, tx1), max(y1, ty1)
            cx2, cy2 = min(x2, tx2), min(y2, ty2)
            filtered.append((cx1, cy1, cx2, cy2))
            x_edges.add(cx1)
            x_edges.add(cx2)
            y_edges.add(cy1)
            y_edges.add(cy2)

        # Step 2: Deduplicate edges within tolerance, then sort
        def dedup(edges):
            s = sorted(edges)
            out = [s[0]]
            for v in s[1:]:
                if v - out[-1] > tol:
                    out.append(v)
            return out

        x_list = dedup(x_edges)
        y_list = dedup(y_edges)

        # Step 3: Check each cell in the grid is covered by at least one rectangle
        for i in range(len(x_list) - 1):
            for j in range(len(y_list) - 1):
                cx1, cx2 = x_list[i], x_list[i + 1]
                cy1, cy2 = y_list[j], y_list[j + 1]

                if not (tx1 <= cx1 + tol and cx2 <= tx2 + tol and ty1 <= cy1 + tol and cy2 <= ty2 + tol):
                    continue

                covered = any(
                    rx1 <= cx1 + tol and rx2 >= cx2 - tol and ry1 <= cy1 + tol and ry2 >= cy2 - tol
                    for rx1, ry1, rx2, ry2 in filtered
                )
                if not covered:
                    return False

        return True

    def cover_all_components(self): 

        self.component['error'] = 0 
        self.fov['error'] = 0 

        comp_big_mask = [0] * len(self.component)
        comp_mask = [0] * len(self.component)

        error_component_list = []

        side_fov_w = self.fov_width / 2.0
        side_fov_h = self.fov_height / 2.0

        big_comp_idx = dict()
        for i, comp in self.component.iterrows():
                tl_x = comp['tl_x']
                tl_y = comp['tl_y']
                br_x = comp['br_x']
                br_y = comp['br_y']
                is_side = comp.get('side', 0) == 1

                eff_w = side_fov_w if is_side else self.fov_width
                eff_h = side_fov_h if is_side else self.fov_height

                n_width, n_height = 1, 1

                if (br_x - tl_x) > eff_w:
                    n_width = math.ceil((br_x - tl_x) / eff_w)

                if (br_y - tl_y) > eff_h:
                    n_height = math.ceil((br_y - tl_y) / eff_h)

                if n_width > 1 or n_height > 1:
                    comp_big_mask[i] = 1
                    big_comp_idx[i] = []

        for i, fov in self.fov.iterrows():
            comp_idx = json.loads(fov['comp_idx'])
            for idx in comp_idx:
                if idx in list(big_comp_idx.keys()):
                    is_side = self.component.iloc[idx].get('side', 0) == 1
                    if is_side:
                        fov_rect = (i, fov['x'] - side_fov_w / 2.0,
                                    fov['y'] - side_fov_h / 2.0,
                                    fov['x'] + side_fov_w / 2.0,
                                    fov['y'] + side_fov_h / 2.0)
                    else:
                        fov_rect = (i,) + tuple(self.fov[['tl_x', 'tl_y', 'br_x', 'br_y']].iloc[i])
                    big_comp_idx[idx].append(fov_rect)

        for k, v in big_comp_idx.items():
            # k: comp idx, v: list of fov rect
            comp_rect = tuple(self.component[['tl_x', 'tl_y', 'br_x', 'br_y']].iloc[k])
            success = self.is_target_fully_covered(v, comp_rect)
            if success:
                comp_mask[k] = 1
            else:
                self.logger.error(f"{k} is out of multiple FOVs.")
                self.component.at[k, 'error'] = 1
                for v_ in v:
                    self.fov.at[v_[0], 'error'] = 1
                error_component_list.append(str(k))
        
        success = True

        for i, fov in self.fov.iterrows():

            fov_tl_x = fov['tl_x'] - 1e-5
            fov_tl_y = fov['tl_y'] - 1e-5
            fov_br_x = fov['br_x'] + 1e-5
            fov_br_y = fov['br_y'] + 1e-5

            side_tl_x = fov['x'] - side_fov_w / 2.0 - 1e-5
            side_tl_y = fov['y'] - side_fov_h / 2.0 - 1e-5
            side_br_x = fov['x'] + side_fov_w / 2.0 + 1e-5
            side_br_y = fov['y'] + side_fov_h / 2.0 + 1e-5

            comp_idx = json.loads(fov['comp_idx'])

            for idx in comp_idx:

                if idx >= len(self.component):
                    self.logger.error(f'Component idx {idx} in FOV {i} is not existed.')
                    continue

                if comp_big_mask[idx] == 1:
                    continue

                comp_tl_x = self.component.iloc[idx]['tl_x']
                comp_tl_y = self.component.iloc[idx]['tl_y']
                comp_br_x = self.component.iloc[idx]['br_x']
                comp_br_y = self.component.iloc[idx]['br_y']
                is_side = self.component.iloc[idx].get('side', 0) == 1

                if is_side:
                    check_tl_x, check_tl_y = side_tl_x, side_tl_y
                    check_br_x, check_br_y = side_br_x, side_br_y
                else:
                    check_tl_x, check_tl_y = fov_tl_x, fov_tl_y
                    check_br_x, check_br_y = fov_br_x, fov_br_y

                if check_tl_x <= comp_tl_x and check_tl_y <= comp_tl_y and check_br_x >= comp_br_x and check_br_y >= comp_br_y:
                    comp_mask[idx] = 1
                else:
                    success = False
                    label = f"{idx} (side)" if is_side else str(idx)
                    self.logger.error(f"{label} is out of FOV.")
                    self.component.at[idx, 'error'] = 1
                    self.fov.at[i, 'error'] = 1
                    error_component_list.append(str(idx))

                
        self._comp_mask = comp_mask

        if sum(comp_mask) != len(self.component):
            n_violation = len(self.component) - sum(comp_mask)
            if n_violation > 0:
                for idx in range(len(self.component)):
                    if comp_mask[idx] == 0:
                        self.component.at[idx, 'error'] = 1
                        error_component_list.append(str(idx))
                self.logger.error(f"{n_violation} components (" + ','.join(error_component_list) + ") is violated the conditions.")
                success = False

        if 'step' in self.component.columns:
            for i, fov in self.fov.iterrows():
                comp_idx = json.loads(fov['comp_idx'])
                comp_idx = [idx for idx in comp_idx if idx < len(self.component)]
                if len(comp_idx) == 0:
                    continue
                steps = set(int(self.component.iloc[idx]['step']) for idx in comp_idx)
                if len(steps) > 1:
                    self.logger.error(f"FOV {i} has mixed step levels: {steps}")
                    self.fov.at[i, 'error'] = 1
                    success = False


        return success 

    def fov_inspection_order(self):
        success = all(self.fov['type'].iloc[i] >= self.fov['type'].iloc[i+1] for i in range(len(self.fov)-1))
        if not success:
            self.logger.error('FOV Inspection order violation.')
        return success

    def penalty_solver(self):
        """Greedy FOV placement for unassigned components only.
        Keeps the original solver FOVs and appends new FOVs for components
        that were not covered (comp_mask == 0).
        """
        import numpy as np

        comp_mask = getattr(self, '_comp_mask', None)
        if comp_mask is None:
            return

        unassigned = [i for i, v in enumerate(comp_mask) if v == 0]
        if not unassigned:
            return

        comp = self.component
        n = len(comp)
        fov_w, fov_h = self.fov_width, self.fov_height
        pcb_w, pcb_h = self.pcb_width, self.pcb_height
        side_fw, side_fh = fov_w / 2.0, fov_h / 2.0

        comp_cx = ((comp['tl_x'] + comp['br_x']) / 2.0).values
        comp_cy = ((comp['tl_y'] + comp['br_y']) / 2.0).values
        comp_w = (comp['br_x'] - comp['tl_x']).values
        comp_h = (comp['br_y'] - comp['tl_y']).values
        c_type = comp['type'].astype(int).values
        c_side = comp['side'].astype(int).values if 'side' in comp.columns else np.zeros(n, dtype=int)
        c_step = comp['step'].astype(int).values if 'step' in comp.columns else np.zeros(n, dtype=int)
        c_tl_x, c_tl_y = comp['tl_x'].values, comp['tl_y'].values
        c_br_x, c_br_y = comp['br_x'].values, comp['br_y'].values
        is_big = np.where(c_side == 1,
                         (comp_w > side_fw) | (comp_h > side_fh),
                         (comp_w > fov_w) | (comp_h > fov_h))

        assigned = [True] * n
        for i in unassigned:
            assigned[i] = False

        new_fovs = []

        dist = np.sqrt(comp_cx ** 2 + comp_cy ** 2)
        order = np.argsort(dist)

        for seed_i in order:
            if assigned[seed_i] or is_big[seed_i]:
                continue

            fx = c_tl_x[seed_i] + fov_w / 2
            fy = c_tl_y[seed_i] + fov_h / 2

            f_tl_x, f_tl_y = fx - fov_w / 2, fy - fov_h / 2
            f_br_x, f_br_y = fx + fov_w / 2, fy + fov_h / 2
            s_tl_x, s_tl_y = fx - side_fw / 2, fy - side_fh / 2
            s_br_x, s_br_y = fx + side_fw / 2, fy + side_fh / 2

            seed_step = int(c_step[seed_i])
            covered = []

            for j in order:
                if assigned[j] or is_big[j]:
                    continue
                if c_step[j] != seed_step:
                    continue
                if c_side[j] == 1:
                    ctl_x, ctl_y, cbr_x, cbr_y = s_tl_x, s_tl_y, s_br_x, s_br_y
                else:
                    ctl_x, ctl_y, cbr_x, cbr_y = f_tl_x, f_tl_y, f_br_x, f_br_y
                tol = 1e-5
                if (ctl_x - tol <= c_tl_x[j] and ctl_y - tol <= c_tl_y[j] and
                        cbr_x + tol >= c_br_x[j] and cbr_y + tol >= c_br_y[j]):
                    covered.append(j)

            if covered:
                for j in covered:
                    assigned[j] = True
                new_fovs.append({'x': fx, 'y': fy, 'comp_idx': covered, 'step': seed_step})

        for i in range(n):
            if assigned[i]:
                continue
            cw, ch = comp_w[i], comp_h[i]
            eff_w = side_fw if c_side[i] == 1 else fov_w
            eff_h = side_fh if c_side[i] == 1 else fov_h
            n_x = math.ceil(cw / eff_w) if cw > eff_w else 1
            n_y = math.ceil(ch / eff_h) if ch > eff_h else 1
            if n_x == 1 and n_y == 1:
                fx = comp_cx[i]
                fy = comp_cy[i]
                new_fovs.append({'x': fx, 'y': fy, 'comp_idx': [i], 'step': int(c_step[i])})
            else:
                for gx in range(n_x):
                    for gy in range(n_y):
                        fx = c_tl_x[i] + eff_w / 2 + gx * eff_w
                        fy = c_tl_y[i] + eff_h / 2 + gy * eff_h
                        fx = min(fx, c_br_x[i] - eff_w / 2)
                        fy = min(fy, c_br_y[i] - eff_h / 2)
                        new_fovs.append({'x': fx, 'y': fy, 'comp_idx': [i], 'step': int(c_step[i])})
            assigned[i] = True

        if not new_fovs:
            return

        for f in new_fovs:
            f['type'] = max((int(c_type[j]) for j in f['comp_idx']), default=0)

        # Nearest-neighbor order among new FOVs, starting from last original FOV
        if len(self.fov) > 0:
            last_row = self.fov.iloc[-1]
            lx, ly = float(last_row['x']), float(last_row['y'])
        else:
            lx, ly = 0.0, 0.0

        remaining = list(new_fovs)
        ordered_new = []
        while remaining:
            best = min(range(len(remaining)),
                       key=lambda j: (remaining[j]['x'] - lx) ** 2 + (remaining[j]['y'] - ly) ** 2)
            chosen = remaining.pop(best)
            ordered_new.append(chosen)
            lx, ly = chosen['x'], chosen['y']

        new_rows = []
        for f in ordered_new:
            new_rows.append({
                'x': f['x'], 'y': f['y'],
                'comp_idx': json.dumps([int(x) for x in f['comp_idx']]),
                'type': f['type'], 'step': f['step']
            })
        new_df = pd.DataFrame(new_rows)
        new_df['tl_x'] = new_df['x'] - fov_w / 2
        new_df['tl_y'] = new_df['y'] - fov_h / 2
        new_df['br_x'] = new_df['x'] + fov_w / 2
        new_df['br_y'] = new_df['y'] + fov_h / 2
        new_df['error'] = 0

        self.fov = pd.concat([self.fov, new_df], ignore_index=True)

        # Recompute FOV type from actual comp_idx contents
        for i in range(len(self.fov)):
            cidx = json.loads(self.fov.iloc[i]['comp_idx'])
            max_t = 0
            for idx in cidx:
                if idx < len(self.component):
                    max_t = max(max_t, int(self.component.iloc[idx]['type']))
            self.fov.at[i, 'type'] = max_t

        # Fix inspection order: type descending (Fiducial=2 → Barcode=1 → Normal=0)
        self.fov = self.fov.sort_values('type', ascending=False, kind='mergesort').reset_index(drop=True)

    def _compute_axis_time(self, distance, vel, acc):
        """Compute travel time along a single axis."""
        th = vel ** 2 / acc
        mask = (distance >= th).astype(float)
        over = 2 * vel / acc + (distance - th) / vel
        under = 2 * np.sqrt(distance / acc)
        return over * mask + under * (1 - mask)

    def _compute_cost_map(self, point, vel_x, vel_y, acc_x, acc_y):
        """Compute max-axis travel time between all point pairs."""
        px = point[:, 0]
        py = point[:, 1]
        dist_x = np.abs(px[:, None] - px[None, :])
        dist_y = np.abs(py[:, None] - py[None, :])
        time_x = self._compute_axis_time(dist_x, vel_x, acc_x)
        time_y = self._compute_axis_time(dist_y, vel_y, acc_y)
        return np.maximum(time_x, time_y)


    def get_real_cost(self, param, point, t_img, t_recon, t_comp, max_core, fov_steps=None):

        vel_x, vel_y, acc_x, acc_y = param
        seqlen = len(point)

        # total distance
        dist = np.sum(np.sqrt(np.sum((point[1:] - point[:-1])**2, axis=1)))
        cost_map = self._compute_cost_map(point, vel_x, vel_y, acc_x, acc_y)

        # first fov's imaging time
        v_core = [0]
        t_start = [0]
        t_duration = [t_img[0].item()]
        v_key = [1]
        v_fov = [0] 
        t_check = np.zeros((seqlen))
        t_last = np.repeat(t_img[0:1], max_core) 

        # first fov's recon (Core 1 or 2)
        recon_t = t_last[1:3]
        recon_core = np.argmin(recon_t) + 1
        v_core.append(recon_core)
        t_start.append(t_img[0])
        t_duration.append(t_recon[0])
        v_key.append(2)
        v_fov.append(0)
        t_last[recon_core] += t_recon[0]

        # first fov's components inspection time
        select_t_last = t_last[recon_core]

        each_t = t_comp[0]

        for j in range(len(each_t)):
            temp_t_last = np.maximum(t_last, select_t_last)
            temp_t_last  = temp_t_last[3:]
            current_id = np.argmin(temp_t_last) + 3

            v_core.append(current_id)
            start_comp = max(select_t_last, t_last[current_id]) 
            t_start.append(start_comp)
            t_duration.append(each_t[j])
            v_key.append(3)
            v_fov.append(0) 
            t_last[current_id] = max(t_last[current_id], select_t_last) + each_t[j]
            t_check[0] = max(t_check[0], t_last[current_id])


        for i in range(seqlen - 1):
            # movement
            t_move = cost_map[i, i + 1]
            v_core.append(0)
            t_start.append(t_last[0])
            t_duration.append(t_move)
            v_key.append(0)
            v_fov.append(i+1)
            t_last[0] += t_move

            # Z-transition delay
            if fov_steps is not None and fov_steps[i] != fov_steps[i + 1]:
                v_core.append(0)
                t_start.append(t_last[0])
                t_duration.append(5.0)
                v_key.append(4)
                v_fov.append(i + 1)
                t_last[0] += 5.0

            # imaging time
            t_check[:] = np.maximum(t_check, t_last[0])
            t_img_start = t_last[0]

            v_core.append(0)
            t_start.append(t_img_start)
            t_duration.append(t_img[i + 1])
            v_key.append(1)
            v_fov.append(i+1) 
            t_last[0] = t_img_start + t_img[i + 1]

            # fov recon (Core 1 or 2)
            t_last[:] = np.maximum(t_last, t_last[0])
            recon_t = np.maximum(t_last, t_last[0])[1:3]
            recon_core = np.argmin(recon_t) + 1

            v_core.append(recon_core)
            t_start.append(t_last[recon_core])
            t_duration.append(t_recon[i + 1])
            v_key.append(2)
            v_fov.append(i+1)
            t_last[recon_core] += t_recon[i + 1]

            # fov's components inspection time
            select_t_last = t_last[recon_core]
            each_t = t_comp[i + 1]

            for j in range(len(each_t)):

                temp_t_last = np.maximum(t_last, select_t_last)
                temp_t_last  = temp_t_last[3:]
                current_id = np.argmin(temp_t_last) + 3

                v_core.append(current_id)

                start_comp = max(select_t_last, t_last[current_id])
                t_start.append(start_comp)
                t_duration.append(each_t[j])
                v_key.append(3)
                v_fov.append(i+1)
                t_last[current_id] = max(t_last[current_id], select_t_last) + each_t[j]
                t_check[i+1] = max(t_check[i+1], t_last[current_id])

        result = {}
        result['t_start'] = t_start
        result['t_duration'] = t_duration
        result['v_core'] = v_core
        result['v_key'] = v_key
        result['v_fov'] = v_fov 

        result = pd.DataFrame(data=result)

        return max(t_last), result

    def compute_ct(self):
        self.fov['imaging_time'] = self.parameter['capture_time'].iloc[0]
        self.fov['recon_time'] = self.parameter['recon_time'].iloc[0]
        if 'side_capture_time' in self.parameter.columns:
            side_capture_time = self.parameter['side_capture_time'].iloc[0] if 'side_capture_time' in self.parameter.columns else self.parameter['capture_time'].iloc[0] / 2
        else:
            side_capture_time = self.parameter['capture_time'].iloc[0] / 2
        fov_center = self.fov[['x', 'y']].to_numpy()
        t_comps = []
        for i in range(len(self.fov)):
            comp_idx = json.loads(self.fov.iloc[i]['comp_idx'])
            comp_idx = [idx for idx in comp_idx if idx < len(self.component)]
            fov_component_df = self.component.iloc[comp_idx]
            t_comps.append(fov_component_df['time'].tolist())
            if any(self.component.iloc[idx]['side'] == 1 for idx in comp_idx if 'side' in self.component.columns):
                self.fov.at[i, 'imaging_time'] = max(self.fov.at[i, 'imaging_time'], side_capture_time)
        t_imaging = self.fov['imaging_time'].to_numpy()
        t_recon = self.fov['recon_time'].to_numpy()
        params = [self.parameter['v_x'].iloc[0], self.parameter['v_y'].iloc[0],
                  self.parameter['a_x'].iloc[0], self.parameter['a_y'].iloc[0]]
        fov_steps = []
        for i in range(len(self.fov)):
            cidx = json.loads(self.fov.iloc[i]['comp_idx'])
            cidx = [idx for idx in cidx if idx < len(self.component)]
            if len(cidx) > 0 and 'step' in self.component.columns:
                fov_steps.append(int(self.component.iloc[cidx[0]]['step']))
            else:
                fov_steps.append(0)
        max_core = int(self.parameter['max_core'].iloc[0])
        self._optimal_core = max_core
        sim_ct, _ = self.get_real_cost(params, fov_center, t_imaging, t_recon, t_comps, max_core=max_core, fov_steps=fov_steps)
        return sim_ct

    def save_combined_view(self, sim_ct=None, sim_gantt=None):
        if sim_ct is None or sim_gantt is None:
            self.fov['imaging_time'] = self.parameter['capture_time'].iloc[0]
            self.fov['recon_time'] = self.parameter['recon_time'].iloc[0]
            side_capture_time = self.parameter['side_capture_time'].iloc[0] if 'side_capture_time' in self.parameter.columns else self.parameter['capture_time'].iloc[0] / 2
            fov_center = self.fov[['x', 'y']].to_numpy()

            t_comps = []
            for i in range(len(self.fov)):
                comp_idx = json.loads(self.fov.iloc[i]['comp_idx'])
                comp_idx = [idx for idx in comp_idx if idx < len(self.component)]
                fov_component_df = self.component.iloc[comp_idx]
                t_comp = fov_component_df['time'].tolist()
                t_comps.append(t_comp)
                if 'side' in self.component.columns and any(self.component.iloc[idx]['side'] == 1 for idx in comp_idx):
                    self.fov.at[i, 'imaging_time'] = max(self.fov.at[i, 'imaging_time'], side_capture_time)

            t_imaging = self.fov['imaging_time'].to_numpy()
            t_recon = self.fov['recon_time'].to_numpy()

            fov_steps = []
            for i in range(len(self.fov)):
                cidx = json.loads(self.fov.iloc[i]['comp_idx'])
                cidx = [idx for idx in cidx if idx < len(self.component)]
                if len(cidx) > 0 and 'step' in self.component.columns:
                    fov_steps.append(int(self.component.iloc[cidx[0]]['step']))
                else:
                    fov_steps.append(0)

            params = [self.parameter['v_x'].iloc[0], self.parameter['v_y'].iloc[0],
                      self.parameter['a_x'].iloc[0], self.parameter['a_y'].iloc[0]]
            max_core = int(self.parameter['max_core'].iloc[0])
            self._optimal_core = max_core
            sim_ct, sim_gantt = self.get_real_cost(params, fov_center, t_imaging, t_recon, t_comps, max_core=max_core, fov_steps=fov_steps)

        err = self.component['error'] if 'error' in self.component.columns else []
        cover = not any(err)
        order = all(self.fov['type'].iloc[i] >= self.fov['type'].iloc[i+1] for i in range(len(self.fov)-1))

        components = []
        for _, row in self.component.iterrows():
            components.append({
                'tl_x': float(row['tl_x']), 'tl_y': float(row['tl_y']),
                'br_x': float(row['br_x']), 'br_y': float(row['br_y']),
                'type': int(row['type']), 'side': int(row.get('side', 0)),
                'step': int(row.get('step', 0)), 'error': int(row.get('error', 0))
            })

        fovs = []
        for i, row in self.fov.iterrows():
            cidx = json.loads(row['comp_idx'])
            has_side = 'side' in self.component.columns and any(self.component.iloc[c]['side'] == 1 for c in cidx if c < len(self.component))
            fovs.append({
                'x': float(row['x']), 'y': float(row['y']),
                'tl_x': float(row['tl_x']), 'tl_y': float(row['tl_y']),
                'br_x': float(row['br_x']), 'br_y': float(row['br_y']),
                'type': int(row['type']), 'error': int(row.get('error', 0)),
                'comp_idx': cidx, 'has_side': has_side
            })

        gantt = []
        for _, row in sim_gantt.iterrows():
            gantt.append({
                'core': int(row['v_core']), 'start': float(row['t_start']),
                'duration': float(row['t_duration']), 'key': int(row['v_key']),
                'fov_idx': int(row['v_fov'])
            })

        step_regions = []
        for _, row in self.step_regions.iterrows():
            step_regions.append({
                'tl_x': float(row['tl_x']), 'tl_y': float(row['tl_y']),
                'br_x': float(row['br_x']), 'br_y': float(row['br_y'])
            })

        data = {
            'pcb': {'width': float(self.pcb_width), 'height': float(self.pcb_height)},
            'fov_size': {'width': float(self.fov_width), 'height': float(self.fov_height)},
            'side_fov_size': {'width': float(self.fov_width) / 2.0, 'height': float(self.fov_height) / 2.0},
            'step_regions': step_regions,
            'components': components,
            'fovs': fovs,
            'gantt': gantt,
            'summary': {
                'ct': round(float(sim_ct), 2),
                'cover': cover,
                'order': order,
                'n_fovs': len(fovs)
            }
        }

        html = self._build_html(data)
        with open(os.path.join(self.folder, 'result.html'), 'w', encoding='utf-8') as f:
            f.write(html)

        return sim_ct

    def _build_html(self, data):
        data_json = json.dumps(data)
        return f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>PCB Inspection Result</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#fff; color:#333; height:100vh; display:flex; flex-direction:column; }}
#header {{ background:#f5f5f5; padding:8px 16px; display:flex; align-items:center; gap:20px; border-bottom:1px solid #ddd; }}
#header h3 {{ color:#d63031; margin:0; }}
.badge {{ padding:3px 10px; border-radius:4px; font-size:13px; font-weight:600; }}
.badge-ok {{ background:#d4edda; color:#155724; }}
.badge-fail {{ background:#f8d7da; color:#721c24; }}
#main {{ display:flex; flex:1; overflow:hidden; }}
#pcb-panel {{ flex:0 0 62%; position:relative; border-right:1px solid #ddd; }}
#timing-panel {{ flex:1; display:flex; flex-direction:column; }}
canvas {{ display:block; }}
#pcb-canvas {{ width:100%; height:100%; cursor:crosshair; }}
#timing-header {{ display:none; }}
#timing-canvas {{ flex:1; width:100%; cursor:pointer; }}
#info {{ background:#f5f5f5; padding:6px 12px; font-size:12px; border-top:1px solid #ddd; color:#666; min-height:24px; }}
.z-btn {{ padding:3px 12px; border:1px solid #bbb; border-radius:4px; font-size:12px; font-weight:600; cursor:pointer; background:#fff; color:#555; margin-left:4px; }}
.z-btn.active {{ background:#e67e00; color:#fff; border-color:#c06000; }}
</style></head><body>
<div id="header">
  <h3>PCB Inspection Viewer</h3>
  <span>FOVs: <b id="s-fovs"></b></span>
  <span>CT: <b id="s-ct"></b>s</span>
  <span>Cover: <span id="s-cover" class="badge"></span></span>
  <span>Order: <span id="s-order" class="badge"></span></span>
  <span style="margin-left:12px;">Step:
    <button class="z-btn active" id="z-all" onclick="setStepFilter(-1)">All</button>
    <button class="z-btn" id="z-0" onclick="setStepFilter(0)">Step=0</button>
    <button class="z-btn" id="z-1" onclick="setStepFilter(1)">Step=1</button>
  </span>
</div>
<div id="main">
  <div id="pcb-panel"><canvas id="pcb-canvas"></canvas></div>
  <div id="timing-panel">
    <div id="timing-header"></div>
    <canvas id="timing-canvas"></canvas>
    <div id="info">&nbsp;</div>
  </div>
</div>
<script>
const D = {data_json};

const S = D.summary;
document.getElementById('s-fovs').textContent = S.n_fovs;
document.getElementById('s-ct').textContent = S.ct;
const sCover = document.getElementById('s-cover');
sCover.textContent = S.cover ? 'PASS' : 'FAIL';
sCover.className = 'badge ' + (S.cover ? 'badge-ok' : 'badge-fail');
const sOrder = document.getElementById('s-order');
sOrder.textContent = S.order ? 'PASS' : 'FAIL';
sOrder.className = 'badge ' + (S.order ? 'badge-ok' : 'badge-fail');

let selectedFov = -1;
let stepFilter = -1;
const info = document.getElementById('info');

function setStepFilter(v) {{
  stepFilter = v;
  selectedFov = -1;
  document.querySelectorAll('.z-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(v === -1 ? 'z-all' : ('z-' + v)).classList.add('active');
  drawPcb(); drawTiming();
}}

function fovMatchesStep(fi) {{
  if (stepFilter === -1) return true;
  const f = D.fovs[fi];
  for (let ci of f.comp_idx) {{
    if (ci < D.components.length && D.components[ci].step === stepFilter) return true;
  }}
  return false;
}}

function compMatchesStep(ci) {{
  if (stepFilter === -1) return true;
  return D.components[ci].step === stepFilter;
}}

// ── PCB Canvas ──
const pcbC = document.getElementById('pcb-canvas');
const pcbCtx = pcbC.getContext('2d');
let pcbBaseScale = 1, pcbBaseOx = 0, pcbBaseOy = 0;
let pcbScale = 1, pcbOx = 0, pcbOy = 0;
let zoomX1 = 0, zoomY1 = 0, zoomX2 = 0, zoomY2 = 0;
let viewMinX = 0, viewMinY = 0, viewMaxX = 0, viewMaxY = 0;
let isZoomed = false, isDragging = false;

function resizePcb() {{
  const r = pcbC.parentElement.getBoundingClientRect();
  pcbC.width = r.width * devicePixelRatio;
  pcbC.height = r.height * devicePixelRatio;
  pcbC.style.width = r.width + 'px';
  pcbC.style.height = r.height + 'px';
  if (!isZoomed) {{
    resetZoom();
  }} else {{
    applyZoom(viewMinX, viewMinY, viewMaxX, viewMaxY);
  }}
}}

function resetZoom() {{
  const pad = 20 * devicePixelRatio;
  const sx = (pcbC.width - 2*pad) / D.pcb.width;
  const sy = (pcbC.height - 2*pad) / D.pcb.height;
  pcbBaseScale = Math.min(sx, sy);
  pcbBaseOx = (pcbC.width - D.pcb.width * pcbBaseScale) / 2;
  pcbBaseOy = (pcbC.height - D.pcb.height * pcbBaseScale) / 2;
  pcbScale = pcbBaseScale; pcbOx = pcbBaseOx; pcbOy = pcbBaseOy;
  viewMinX = 0; viewMinY = 0; viewMaxX = D.pcb.width; viewMaxY = D.pcb.height;
  isZoomed = false;
}}

function applyZoom(x1, y1, x2, y2) {{
  const pad = 10 * devicePixelRatio;
  const w = Math.abs(x2-x1) || 1, h = Math.abs(y2-y1) || 1;
  const sx = (pcbC.width - 2*pad) / w;
  const sy = (pcbC.height - 2*pad) / h;
  pcbScale = Math.min(sx, sy);
  const cx = (Math.min(x1,x2) + Math.max(x1,x2)) / 2;
  const cy = (Math.min(y1,y2) + Math.max(y1,y2)) / 2;
  pcbOx = pcbC.width/2 - cx * pcbScale;
  pcbOy = pcbC.height/2 - cy * pcbScale;
  viewMinX = Math.min(x1,x2); viewMinY = Math.min(y1,y2);
  viewMaxX = Math.max(x1,x2); viewMaxY = Math.max(y1,y2);
  isZoomed = true;
}}

function px(x) {{ return pcbOx + x * pcbScale; }}
function py(y) {{ return pcbOy + y * pcbScale; }}
function invPx(sx) {{ return (sx - pcbOx) / pcbScale; }}
function invPy(sy) {{ return (sy - pcbOy) / pcbScale; }}

function drawPcb() {{
  const ctx = pcbCtx;
  ctx.clearRect(0, 0, pcbC.width, pcbC.height);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, pcbC.width, pcbC.height);

  // PCB border
  ctx.strokeStyle = '#999';
  ctx.lineWidth = 1;
  ctx.strokeRect(px(0), py(0), D.pcb.width*pcbScale, D.pcb.height*pcbScale);

  // Step regions overlay
  if (D.step_regions && D.step_regions.length > 0) {{
    D.step_regions.forEach((sr, si) => {{
      const x = px(sr.tl_x), y = py(sr.tl_y);
      const w = (sr.br_x - sr.tl_x) * pcbScale;
      const h = (sr.br_y - sr.tl_y) * pcbScale;
      ctx.fillStyle = 'rgba(180,140,60,0.12)';
      ctx.fillRect(x, y, w, h);
      ctx.strokeStyle = 'rgba(160,120,40,0.5)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 4]);
      ctx.strokeRect(x, y, w, h);
      ctx.setLineDash([]);
      ctx.fillStyle = 'rgba(140,100,20,0.65)';
      ctx.font = 'bold ' + Math.max(11*devicePixelRatio, pcbScale*4) + 'px sans-serif';
      ctx.textAlign = 'left'; ctx.textBaseline = 'top';
      ctx.fillText('Step=1', x + 4*devicePixelRatio, y + 4*devicePixelRatio);
    }});
  }}

  // FOV boxes
  D.fovs.forEach((f, i) => {{
    ctx.save();
    const matchStep = fovMatchesStep(i);
    const dimmed = !matchStep;
    ctx.globalAlpha = dimmed ? 0.08 : 1.0;
    const isSel = (i === selectedFov) && matchStep;
    if (f.error) ctx.fillStyle = 'rgba(205,99,71,0.2)';
    else if (isSel) ctx.fillStyle = 'rgba(255,180,0,0.3)';
    else if (f.type === 2) ctx.fillStyle = 'rgba(0,153,25,0.15)';
    else if (f.type === 1) ctx.fillStyle = 'rgba(128,0,128,0.15)';
    else ctx.fillStyle = 'rgba(0,0,0,0.06)';
    const x1=px(f.tl_x), y1=py(f.tl_y), w=(f.br_x-f.tl_x)*pcbScale, h=(f.br_y-f.tl_y)*pcbScale;
    ctx.fillRect(x1,y1,w,h);
    ctx.strokeStyle = isSel ? '#e67e00' : (f.error ? '#cd4547' : '#aaa');
    ctx.lineWidth = isSel ? 2.5 : 0.8;
    ctx.strokeRect(x1,y1,w,h);
    if (!dimmed) {{
      ctx.fillStyle = isSel ? '#c06000' : 'rgba(0,0,0,0.25)';
      ctx.font = (isSel ? 'bold ' : '') + Math.max(9*devicePixelRatio, pcbScale*3.5) + 'px sans-serif';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(i, x1+w/2, y1+h/2);
    }}
    if (f.has_side && !dimmed) {{
      const sw = D.side_fov_size.width * pcbScale;
      const sh = D.side_fov_size.height * pcbScale;
      const sx = px(f.x) - sw/2;
      const sy = py(f.y) - sh/2;
      ctx.fillStyle = isSel ? 'rgba(40,80,220,0.2)' : 'rgba(40,80,220,0.1)';
      ctx.fillRect(sx, sy, sw, sh);
      ctx.strokeStyle = isSel ? '#2255cc' : '#4477cc';
      ctx.lineWidth = isSel ? 2 : 1;
      ctx.setLineDash([4, 3]);
      ctx.strokeRect(sx, sy, sw, sh);
      ctx.setLineDash([]);
    }}
    ctx.restore();
  }});

  // components
  D.components.forEach((c, ci) => {{
    const matchStep = compMatchesStep(ci);
    ctx.globalAlpha = matchStep ? 1.0 : 0.08;
    const w = (c.br_x-c.tl_x)*pcbScale, h = (c.br_y-c.tl_y)*pcbScale;
    if (c.error) ctx.fillStyle = '#d63031';
    else if (matchStep && selectedFov >= 0 && D.fovs[selectedFov].comp_idx.includes(ci)) ctx.fillStyle = '#e67e00';
    else if (c.type === 2) ctx.fillStyle = '#00a832';
    else if (c.type === 1) ctx.fillStyle = '#8B008B';
    else if (c.side === 1) ctx.fillStyle = '#3366cc';
    else ctx.fillStyle = '#666';
    ctx.fillRect(px(c.tl_x), py(c.tl_y), Math.max(w,1.5), Math.max(h,1.5));
  }});
  ctx.globalAlpha = 1.0;

  // FOV trajectory
  if (D.fovs.length > 1) {{
    ctx.beginPath();
    let started = false;
    for (let i=0; i<D.fovs.length; i++) {{
      if (!fovMatchesStep(i)) continue;
      if (!started) {{ ctx.moveTo(px(D.fovs[i].x), py(D.fovs[i].y)); started = true; }}
      else ctx.lineTo(px(D.fovs[i].x), py(D.fovs[i].y));
    }}
    ctx.strokeStyle = 'rgba(0,0,0,0.45)';
    ctx.lineWidth = 3.0;
    ctx.stroke();
  }}

  // FOV center dots + labels
  ctx.globalAlpha = 1.0;
  const dotR = Math.max(6 * devicePixelRatio, 8);
  D.fovs.forEach((f, i) => {{
    if (!fovMatchesStep(i)) return;
    const isSel = (i === selectedFov);
    const r = isSel ? dotR * 1.6 : (i === 0 ? dotR * 1.3 : dotR);
    ctx.beginPath();
    ctx.arc(px(f.x), py(f.y), r, 0, Math.PI * 2);
    if (isSel) {{
      ctx.fillStyle = '#fff';
      ctx.fill();
      ctx.strokeStyle = '#c06000';
      ctx.lineWidth = 3.0;
      ctx.stroke();
    }} else {{
      if (i === 0) ctx.fillStyle = '#d63031';
      else if (f.type === 2) ctx.fillStyle = '#00a832';
      else if (f.type === 1) ctx.fillStyle = '#8B008B';
      else ctx.fillStyle = 'rgba(0,0,0,0.6)';
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }}
  }});
}}

pcbC.addEventListener('mousedown', e => {{
  const rect = pcbC.getBoundingClientRect();
  zoomX1 = (e.clientX - rect.left) * devicePixelRatio;
  zoomY1 = (e.clientY - rect.top) * devicePixelRatio;
  isDragging = false;
}});

pcbC.addEventListener('mousemove', e => {{
  if (e.buttons !== 1) return;
  const rect = pcbC.getBoundingClientRect();
  zoomX2 = (e.clientX - rect.left) * devicePixelRatio;
  zoomY2 = (e.clientY - rect.top) * devicePixelRatio;
  if (Math.abs(zoomX2-zoomX1) > 5 || Math.abs(zoomY2-zoomY1) > 5) isDragging = true;
  if (isDragging) {{
    drawPcb();
    pcbCtx.strokeStyle = '#e67e00';
    pcbCtx.lineWidth = 1.5;
    pcbCtx.setLineDash([5, 3]);
    pcbCtx.strokeRect(Math.min(zoomX1,zoomX2), Math.min(zoomY1,zoomY2),
      Math.abs(zoomX2-zoomX1), Math.abs(zoomY2-zoomY1));
    pcbCtx.setLineDash([]);
  }}
}});

pcbC.addEventListener('mouseup', e => {{
  const rect = pcbC.getBoundingClientRect();
  const mx = (e.clientX - rect.left) * devicePixelRatio;
  const my = (e.clientY - rect.top) * devicePixelRatio;
  if (isDragging && Math.abs(mx-zoomX1) > 10 && Math.abs(my-zoomY1) > 10) {{
    const x1 = invPx(Math.min(zoomX1, mx)), y1 = invPy(Math.min(zoomY1, my));
    const x2 = invPx(Math.max(zoomX1, mx)), y2 = invPy(Math.max(zoomY1, my));
    applyZoom(x1, y1, x2, y2);
    drawPcb();
  }} else {{
    let hit = -1;
    for (let i = D.fovs.length-1; i>=0; i--) {{
      const f = D.fovs[i];
      if (mx>=px(f.tl_x) && mx<=px(f.br_x) && my>=py(f.tl_y) && my<=py(f.br_y)) {{ hit=i; break; }}
    }}
    selectedFov = (hit === selectedFov) ? -1 : hit;
    drawPcb(); drawTiming();
    info.textContent = selectedFov >= 0
      ? 'FOV ' + selectedFov + ' — components: [' + D.fovs[selectedFov].comp_idx.join(', ') + ']'
      : '';
  }}
  isDragging = false;
}});

pcbC.addEventListener('dblclick', e => {{
  resetZoom();
  drawPcb();
}});

// ── Timing Canvas ──
const tmC = document.getElementById('timing-canvas');
const tmCtx = tmC.getContext('2d');
let tmScale=1, tmOx=40, tmOy=20, tmRowH=1, maxCore=0;

function resizeTm() {{
  const r = tmC.parentElement.getBoundingClientRect();
  const hdr = document.getElementById('timing-header').getBoundingClientRect().height;
  const inf = document.getElementById('info').getBoundingClientRect().height;
  tmC.width = r.width * devicePixelRatio;
  tmC.height = Math.max(100, (r.height - hdr - inf)) * devicePixelRatio;
  tmC.style.width = r.width + 'px';
  tmC.style.height = Math.max(100, (r.height - hdr - inf)) + 'px';

  maxCore = 0;
  D.gantt.forEach(g => {{ if (g.core > maxCore) maxCore = g.core; }});
  const padL = 40 * devicePixelRatio, padR = 20 * devicePixelRatio;
  const padT = 20 * devicePixelRatio, padB = 30 * devicePixelRatio;
  tmOx = padL; tmOy = padT;
  tmScale = (tmC.width - padL - padR) / S.ct;
  tmRowH = (tmC.height - padT - padB) / (maxCore + 1);
}}

const keyColor = ['#1773B2','#2B9F2A','#E26768','#FE9234','#9B59B6'];

function drawTiming() {{
  const ctx = tmCtx;
  ctx.clearRect(0, 0, tmC.width, tmC.height);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, tmC.width, tmC.height);

  // helper: core row y (inverted: core 0 at bottom, maxCore at top)
  function coreY(c) {{ return tmOy + (maxCore - c) * tmRowH; }}

  // grid lines
  ctx.strokeStyle = '#e0e0e0';
  ctx.lineWidth = 0.5;
  for (let c=0; c<=maxCore; c++) {{
    const y = coreY(c);
    ctx.beginPath(); ctx.moveTo(tmOx, y); ctx.lineTo(tmC.width - 10*devicePixelRatio, y); ctx.stroke();
  }}

  // time axis ticks
  const step = Math.max(1, Math.ceil(S.ct / 10));
  ctx.fillStyle = '#666';
  ctx.font = (10*devicePixelRatio) + 'px sans-serif';
  ctx.textAlign = 'center';
  for (let t=0; t<=S.ct; t+=step) {{
    const x = tmOx + t * tmScale;
    ctx.fillText(t + 's', x, tmOy + (maxCore+1)*tmRowH + 15*devicePixelRatio);
  }}

  // core labels
  ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
  for (let c=0; c<=maxCore; c++) {{
    ctx.fillStyle = '#666';
    ctx.fillText('C'+c, tmOx - 5*devicePixelRatio, coreY(c) + tmRowH*0.45);
  }}

  // bars
  const barH = tmRowH * 0.75;
  D.gantt.forEach(g => {{
    const fovMatch = fovMatchesStep(g.fov_idx);
    const isSel = (selectedFov >= 0 && g.fov_idx === selectedFov) && fovMatch;
    const isDim = (selectedFov >= 0 && g.fov_idx !== selectedFov) || !fovMatch;
    ctx.fillStyle = keyColor[g.key] || '#888';
    ctx.globalAlpha = isDim ? (fovMatch ? 0.15 : 0.05) : (isSel ? 1.0 : 0.7);
    const x = tmOx + g.start * tmScale;
    const w = Math.max(g.duration * tmScale, 0.5);
    const y = coreY(g.core) + (tmRowH - barH)/2;
    ctx.fillRect(x, y, w, barH);
    if (isSel) {{
      ctx.strokeStyle = '#e67e00';
      ctx.lineWidth = 1.5;
      ctx.globalAlpha = 1;
      ctx.strokeRect(x, y, w, barH);
    }}
  }});
  ctx.globalAlpha = 1;

  // legend
  const labels = ['Move','Capture','Recon','Inspect','Z-Trans'];
  let lx = tmOx;
  const ly = 8 * devicePixelRatio;
  ctx.font = (9*devicePixelRatio) + 'px sans-serif';
  ctx.textAlign = 'left'; ctx.textBaseline = 'top';
  labels.forEach((l,i) => {{
    ctx.fillStyle = keyColor[i];
    ctx.fillRect(lx, ly, 10*devicePixelRatio, 10*devicePixelRatio);
    ctx.fillStyle = '#444';
    ctx.fillText(l, lx + 13*devicePixelRatio, ly);
    lx += ctx.measureText(l).width + 24*devicePixelRatio;
  }});
}}

tmC.addEventListener('click', e => {{
  const rect = tmC.getBoundingClientRect();
  const mx = (e.clientX - rect.left) * devicePixelRatio;
  const my = (e.clientY - rect.top) * devicePixelRatio;
  let hit = -1;
  const barH = tmRowH * 0.75;
  function coreYClick(c) {{ return tmOy + (maxCore - c) * tmRowH; }}
  for (let i = D.gantt.length-1; i>=0; i--) {{
    const g = D.gantt[i];
    const x = tmOx + g.start * tmScale;
    const w = Math.max(g.duration * tmScale, 2);
    const y = coreYClick(g.core) + (tmRowH - barH)/2;
    if (mx>=x && mx<=x+w && my>=y && my<=y+barH) {{ hit = g.fov_idx; break; }}
  }}
  selectedFov = (hit === selectedFov) ? -1 : hit;
  drawPcb(); drawTiming();
  info.textContent = selectedFov >= 0
    ? 'FOV ' + selectedFov + ' — components: [' + D.fovs[selectedFov].comp_idx.join(', ') + ']'
    : '';
}});

function render() {{ resizePcb(); resizeTm(); drawPcb(); drawTiming(); }}
window.addEventListener('resize', render);
render();
</script></body></html>'''
