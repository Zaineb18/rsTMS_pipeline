from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
import os
import warnings
import numpy as np
import pandas as pd
import simnibs.msh.mesh_io as mesh_io
from simnibs.utils.simnibs_utils import get_field_at_target

# ==========================
# E-field and scalp-to-target distance check after SimNIBS TMS optimisation
#
# To be run after tmsoptim.py.
#
# For each subject and session, this script:
#   1. Locates the FEM result mesh (.msh) produced by TMSoptimize.
#   2. Interpolates the E-field norm (|E|, V/m) at the individualised
#      cortical target in subject space.
#   3. Computes the Euclidean distance from the scalp surface (tag 5)
#      to the target coordinate as a proxy for stimulation depth.
#   4. Logs a warning if |E| falls below E_THRESHOLD, which may indicate
#      that the target is too deep for effective TMS.
#   5. Writes both metrics back into the targeting-results TSV on the
#      row where tissue == 'GM mask' and stat == 'Fisher Z'.
#
# Output columns added to the TSV:
#   e_field_Vm          — |E| at the target in V/m (4 decimal places)
#   scalp_to_target_mm  — Euclidean distance from nearest scalp node
#                         to the target in mm (1 decimal place)
#
# Notes:
#   - SimNIBS tissue tags: WM=1, GM=2, CSF=3, skull=4, scalp=5.
#   - The scalp-to-target distance is computed as the minimum Euclidean
#     distance from all scalp nodes (tag 5) to the target coordinate.
#     This is an approximation; for a stricter perpendicular projection
#     use m.find_closest_element() on the scalp surface mesh.
#   - optim_orientation must match the value used in tmsoptim.py so
#     that pathfem resolves to the correct output directory.
#   - The TSV is re-read at write time to avoid overwriting any
#     columns modified between the two scripts.
# ==========================

optim_orientation = True  # must match tmsoptim.py
E_THRESHOLD = 0.1  # V/m — indicative clinical lower bound

for subject in subjects:
    for session in sessions:

        # --- Reconstruct paths (must match tmsoptim.py) ---
        results_file = os.path.join(RES_PATH, f'sub-{subject}', f'ses-{session}',
                                    f'sub-{subject}_ses-{session}_targeting-results.csv')
        subpath = os.path.join(CHARM_PATH, f'sub-{subject}', f'ses-{session}',
                               f'm2m_sub-{subject}_ses-{session}')

        if optim_orientation:
            pathfem = os.path.join(SIMNIBS_PATH, f'sub-{subject}/ses-{session}',
                                   f'sub-{subject}_ses-{session}_tmsoptim')
        else:
            pathfem = os.path.join(SIMNIBS_PATH, f'sub-{subject}/ses-{session}',
                                   f'sub-{subject}_ses-{session}_tmsoptim_toFront')

        # --- Recover target coordinate from TSV ---
        df = pd.read_csv(results_file, sep='\t')
        subset_df = df[(df["tissue"] == 'GM mask') & (df["stat"] == 'Fisher Z')]
        mni_coords = (int(subset_df['mni_x']), int(subset_df['mni_y']), int(subset_df['mni_z']))
        from simnibs import mni2subject_coords
        target_coords = mni2subject_coords(mni_coords, subpath)

        # --- Load FEM mesh ---
        msh_files = [f for f in os.listdir(pathfem) if f.endswith('.msh')]
        if not msh_files:
            print(f"[{subject} / {session}] No .msh file found in {pathfem}, skipping.")
            continue

        m = mesh_io.read_msh(os.path.join(pathfem, msh_files[0]))

        # --- E-field at target ---
        e_at_target = get_field_at_target(m, target_coords, field_name='normE')

        # --- Scalp-to-target distance ---
        scalp_nodes = m.nodes.node_coord[m.elm.tag1 == 5]
        scalp_to_target_mm = float(np.min(np.linalg.norm(scalp_nodes - target_coords, axis=1)))

        print(f"[{subject} / {session}] |E| at target: {e_at_target:.4f} V/m | "
              f"Scalp-to-target distance: {scalp_to_target_mm:.1f} mm")

        if e_at_target < E_THRESHOLD:
            warnings.warn(
                f"[{subject} / {session}] Low E-field at target "
                f"({e_at_target:.4f} V/m < {E_THRESHOLD} V/m). "
                f"Scalp-to-target distance: {scalp_to_target_mm:.1f} mm — target may be too deep."
            )

        # --- Write metrics back to TSV ---
        df = pd.read_csv(results_file, sep='\t')
        mask = (df["tissue"] == 'GM mask') & (df["stat"] == 'Fisher Z')
        df.loc[mask, 'e_field_Vm']         = round(e_at_target, 4)
        df.loc[mask, 'scalp_to_target_mm'] = round(scalp_to_target_mm, 1)
        df.to_csv(results_file, sep='\t', index=False)