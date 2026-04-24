from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.analysis.logging_utils import *
from rsTMS_pipeline.analysis.analysis_utils import *
import os, sys
from scipy.spatial import cKDTree
from simnibs import opt_struct, mni2subject_coords
from simnibs import localite
import numpy as np
import pandas as pd
import simnibs.mesh_tools.mesh_io as mesh_io
from datetime import datetime


# ==========================
# SimNIBS TMS Coil Position Optimisation for Individualized DLPFC Targeting
#
# Author: Zaineb Amor & Guillaume Goudriet
#
# Context:
#   Once the individualized TMS target MNI coordinate has been identified
#   from functional connectivity analysis, the optimal TMS coil position and orientation
#   must be computed to maximally stimulate that cortical target given the
#   individual subject's head anatomy. This script uses SimNIBS TMSoptimize
#   to solve that problem, using the CHARM head model built from each
#   subject's fMRIPrep T1w image.
#
#   The coil used is the MagVenture Cool-B65 (figure-of-eight), a standard
#   clinical coil used in MDD TMS protocols.
#
# --- Configuration flag ---
#
#   optim_orientation : bool
#     Controls whether coil orientation is optimised jointly with position,
#     or fixed to a predefined anatomical direction.
#
#     True  → Full optimisation (position + orientation).
#             Uses the ADM method (Auxiliary Dipole Method).
#             Searches ~2.1 million configurations (5,900 positions ×
#             360 orientations). Recommended when maximum E-field at the
#             target is the priority. 
#     False → Position-only optimisation (fixed orientation).
#             Orientation is fixed with the coil handle pointing toward
#             the occipital lobe = (-46, 10, 36) or frontal lobe = (-46,82,36) in 
#             MNI space. Sets search_angle = 0 so only
#             scalp position is searched (~5,900 configurations).
#             Uses the SimNIBS grid search method (ADM is not compatible
#             with fixed-orientation search).
#
# This script loops over all subjects and sessions. For each, it:
#
# --- Step 1: Load individualized target coordinate ---
#
#   Reads the targeting results TSV from:
#     RES_PATH/sub-{subject}/ses-{session}/
#       sub-{subject}_ses-{session}_targeting-results.csv
#
#   Filters to the row where:
#     - tissue == 'GM mask'   (most anatomically precise restriction)
#     - stat   == 'Fisher Z'  (most statistically appropriate metric)
#
#   Extracts mni_x, mni_y, mni_z as integer MNI coordinates.
#
# --- Step 2: Configure SimNIBS TMSoptimize ---
#
#   Sets up a TMSoptimize object with the following fields:
#
#   subpath   — path to the subject's CHARM head model directory:
#               CHARM_PATH/sub-{subject}/ses-{session}/
#                 m2m_sub-{subject}_ses-{session}/
#               built by charmtms_bash.sh
#   fnamecoil — path to the MagVenture Cool-B65 coil definition file (.ccd),
#               located in the SimNIBS coil model library.
#               Update this path if the coil or SimNIBS installation changes.
#   pathfem   — output directory for the FEM simulation results.
#               Name reflects the optimisation mode:
#                 *_tmsoptim          → full optimisation (optim_orientation=True)
#                 *_tmsoptim_toOccip  → position-only, handle toward occipital
#                                       pole (optim_orientation=False)
#                 *_tmsoptim_toFront  → position-only, handle toward frontal
#                                       pole (optim_orientation=False)
#   target    — individualized cortical target in subject (T1w) space,
#               converted from MNI via mni2subject_coords(), which applies
#               the inverse MNI→T1w transform stored in the CHARM m2m
#               directory.

#   If optim_orientation is True (full optimisation):
#     method = 'ADM'  — Auxiliary Dipole Method. Leverages electromagnetic
#                       reciprocity and fast multipole acceleration to
#                       evaluate all 2.1M configurations from a single
#                       FEM solve in <15 minutes on a standard laptop.
#
#   If optim_orientation is False (position-only):
#     search_angle = 0     — disables angular sweep; single orientation only
#     pos_ydir             — MNI reference point converted to subject space,
#                            defining the coil handle (y-axis) direction.
#     method               — grid search (ADM is not compatible with fixed
#                            orientation; ADM requires the full 360-degree
#                            orientation sweep to function correctly)
#
# --- Step 3: Run coil position optimisation ---
#
#   Calls tms_opt.run(), which:
#     1. Loads the CHARM head model mesh.
#     2. Runs the selected optimisation (ADM or grid search) to find the
#        coil position (and optionally orientation) that maximises the
#        electric field magnitude at the target coordinate.
#     3. Returns opt_pos: the optimal 4×4 coil-to-head affine matrix.
#
# --- Step 4: Export coil position for neuronavigation ---
#
#   Saves the optimal coil position to a Localite TMS Navigator-compatible
#   file via localite().write() at:
#     tms_opt.pathfem / sub-{subject}_ses-{session}_opt_pos
#
#   np.squeeze() reduces opt_pos from shape (1,4,4) to (4,4) as required
#   by localite().write(). The Localite file encodes the 4×4 coil matrix
#   and can be loaded directly into the Localite TMS Navigator
#   neuronavigation system for coil placement during the TMS session.
#
# Notes:
#   - Run charmtms_bash.sh before this script. 
#   - The targeting results CSV must exist in RES_PATH.
#   - tms_opt is instantiated once outside the loop and reused across
#     subjects and sessions. Fields are overwritten at each iteration.
#   - The coil path is currently hardcoded. Update fnamecoil if the
#     SimNIBS installation path or coil model changes.
#   - To switch between full and position-only optimisation, change only
#     the optim_orientation flag at the top of the script.
#   - To use an anteriorly-directed handle instead, replace toward_occip
#     with toward_front in the pos_ydir assignment.
# ==========================

suffix = datetime.now()
tms_opt = opt_struct.TMSoptimize()
optim_orientation = False
Occip = False
toward_occip = (-46,10,36)
toward_front = (-46,82,36)

for subject in subjects:
    for session in sessions: 
        results_file = os.path.join(RES_PATH, f'sub-{subject}', f'ses-{session}',
                     f'sub-{subject}_ses-{session}_targeting-results.csv')
        log_file = os.path.join(RES_PATH, f'sub-{subject}', f'ses-{session}',
                     f'sub-{subject}_ses-{session}_targeting-log_{suffix}.txt')
        df = pd.read_csv(results_file, sep='\t')
        subset_df = df[(df["tissue"] == 'GM mask') & (df["stat"] == 'Fisher Z')]
        mni_coords = (int(subset_df['mni_x']), int(subset_df['mni_y']), int(subset_df['mni_z']))       
        tms_opt.subpath = os.path.join(CHARM_PATH, f'sub-{subject}', f'ses-{session}', f'm2m_sub-{subject}_ses-{session}')
        tms_opt.fnamecoil ='/home/zaineb/simnibs/resources/coil_models/Drakaki_BrainStim_2022/MagVenture_Cool-B65.ccd'
        if optim_orientation:
            tms_opt.pathfem = os.path.join(SIMNIBS_PATH,f'sub-{subject}/ses-{session}',
                                           f'sub-{subject}_ses-{session}_tmsoptim_{suffix}')
            os.makedirs(tms_opt.pathfem, exist_ok=True)
            tms_opt.target = mni2subject_coords(mni_coords, tms_opt.subpath)
            tms_opt.method = 'ADM'  
        else:
            if Occip:    
                  tms_opt.pathfem = os.path.join(SIMNIBS_PATH,f'sub-{subject}/ses-{session}',
                                           f'sub-{subject}_ses-{session}_tmsoptim_toOccip_{suffix}')
                  orientation = toward_occip
            else: 
                  tms_opt.pathfem = os.path.join(SIMNIBS_PATH,f'sub-{subject}/ses-{session}',
                                           f'sub-{subject}_ses-{session}_tmsoptim_toFront_{suffix}')
                  orientation = toward_front
            os.makedirs(tms_opt.pathfem, exist_ok=True)            
            tms_opt.pos_ydir = mni2subject_coords(orientation, tms_opt.subpath)                        
            tms_opt.target = mni2subject_coords(mni_coords, tms_opt.subpath)
            tms_opt.search_angle = 0

        sys.stdout = Tee(log_file)
        print(f"\n{'█'*60}")
        print(f"█  Subject : {subject}   |   Session : {session}")
        print(f"█  Run at  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'█'*60}")
        # ----------------- Coordinates -----------------
        mni_arr = np.array(mni_coords, dtype=float)
        mni_to_subj_displacement = float(np.linalg.norm(tms_opt.target - mni_arr))
        log_section("Coordinates summary", [
            {'label': 'MNI (standard space)', 'values': mni_coords, 'unit': 'mm'},
            {'label': 'Target — subject T1w', 'values': tms_opt.target, 'unit': 'mm'},
            {'label': 'MNI → subject displacement', 'values': mni_to_subj_displacement, 'unit': 'mm'}
        ])
        # ----------------- Surface localisation -----------------       
        charm_mesh_candidates = [f for f in os.listdir(tms_opt.subpath) if f.endswith('.msh') and not f.startswith('.')]
        if charm_mesh_candidates:
            m_charm = mesh_io.read_msh(os.path.join(tms_opt.subpath,
                                                     charm_mesh_candidates[0]))
            gm_node_indices  = np.unique(m_charm.elm.node_number_list[m_charm.elm.tag1 == 2] - 1)
            gm_coords        = m_charm.nodes.node_coord[gm_node_indices]
            dists_to_gm      = np.linalg.norm(gm_coords - tms_opt.target, axis=1)
            nearest_gm_coord = gm_coords[np.argmin(dists_to_gm)]
            nearest_gm_dist  = float(np.min(dists_to_gm))
            scalp_node_indices  = np.unique(m_charm.elm.node_number_list[m_charm.elm.tag1 == 5] - 1)
            scalp_coords        = m_charm.nodes.node_coord[scalp_node_indices]
            dists_to_scalp      = np.linalg.norm(scalp_coords - tms_opt.target, axis=1)
            nearest_scalp_coord = scalp_coords[np.argmin(dists_to_scalp)]
            scalp_to_target_mm  = float(np.min(dists_to_scalp))
            log_section("Surface localisation", [
                {'label': 'Nearest GM node', 'values': nearest_gm_coord, 'unit': 'mm'},
                {'label': 'd_GM', 'values': nearest_gm_dist, 'unit': 'mm'},
                {'label': 'Nearest scalp node', 'values': nearest_scalp_coord, 'unit': 'mm'},
                {'label': 'd_scalp', 'values': scalp_to_target_mm, 'unit': 'mm'}
            ])
        else:
            print(f"No CHARM mesh found in {tms_opt.subpath} — skipping.")
            scalp_to_target_mm = float('nan')
            nearest_gm_coord = nearest_gm_dist = nearest_scalp_coord = float('nan')
        # ----------------- Coil orientation -----------------
        if not optim_orientation:
            orientation_label = "toward occipital" if Occip else "toward frontal"
            log_section(f"Coil handle direction ({orientation_label})", [
                {'label': 'pos_ydir — subject T1w', 'values': tms_opt.pos_ydir, 'unit': 'mm'}
            ])
        else:
            subsection("Coil orientation will be optimized")
        # ----------------- Running TMSoptimize -----------------
        section("Running TMSoptimize")
        print(f"  pathfem : {tms_opt.pathfem}")
        print(f"  method  : {'ADM (full optimisation)' if optim_orientation else 'grid search (fixed orientation)'}")
        print(f"  coil    : {tms_opt.fnamecoil}")
        tee = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        opt_pos = tms_opt.run()
        sys.stdout.close()
        sys.stdout = tee
        fn = os.path.join(tms_opt.pathfem, f'sub-{subject}_ses-{session}_opt_pos')
        localite().write(np.squeeze(opt_pos), fn)
        # ----------------- E-field calculations -----------------        
        #msh_files = [f for f in os.listdir(tms_opt.pathfem) if f.endswith('.msh')]
        msh_files = [f for f in os.listdir(tms_opt.pathfem) 
             if f.endswith('.msh') and 'TMS_optimize' in f]        
        if not msh_files:
            msh_files = [f for f in os.listdir(tms_opt.pathfem) 
                        if f.endswith('.msh') and not f.startswith(f'sub-{subject}')]
        print("All .msh in pathfem:", os.listdir(tms_opt.pathfem))
        print("Selected result mesh:", msh_files)                         
        if msh_files:
             m_res = mesh_io.read_msh(os.path.join(tms_opt.pathfem, msh_files[0]))
             print("Available fields:", list(m_res.field.keys()))
             efield_full = compute_efield_metrics(m_res, gm_shell=False, shell_mm=1.0)     
             efield_shell = compute_efield_metrics(m_res, gm_shell=True, shell_mm=1.0)     
        else:
             print("No result .msh found in pathfem — E-field metrics unavailable.")
             e_at_target = float('nan')
             e_max_gm    = float('nan')
             e_ratio     = float('nan')

        print_results_summary(opt_pos, tms_opt, mni_coords, nearest_gm_coord, nearest_gm_dist,
                      nearest_scalp_coord, scalp_to_target_mm, mni_to_subj_displacement,
                      efield_full, efield_shell, di_dt_per_MSO=1.2, MSO=100, Occip=Occip,
                      toward_occip=toward_occip, toward_front=toward_front, 
                      optim_orientation=optim_orientation, fn=fn, subject=subject, session=session)
        
        print(f"[log] sub-{subject} / ses-{session} — saved to {log_file}")
        
        m_res = mesh_io.read_msh(os.path.join(tms_opt.pathfem, msh_files[0]))
        vis = m_res.view(visible_tags=[1002],             # GM outer surface — matches GUI default view
                visible_fields='all')
        #vis.View[0].CustomMax = 1
        #vis.View[0].CustomMin = 0
        vis.show()
