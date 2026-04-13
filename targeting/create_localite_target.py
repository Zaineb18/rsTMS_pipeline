from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
import os
from simnibs import opt_struct, mni2subject_coords
from simnibs import localite
import simnibs.msh.mesh_io as mesh_io
from simnibs.utils.simnibs_utils import get_field_at_target
import numpy as np
import pandas as pd

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

tms_opt = opt_struct.TMSoptimize()
optim_orientation = True
toward_occip = (-46,10,36)
toward_front = (-46,82,36)
for subject in subjects:
    for session in sessions: 
        results_file = os.path.join(RES_PATH, f'sub-{subject}', f'ses-{session}',
                     f'sub-{subject}_ses-{session}_targeting-results.csv')
        df = pd.read_csv(results_file, sep='\t')
        subset_df = df[(df["tissue"] == 'GM mask') & (df["stat"] == 'Fisher Z')]
        mni_coords = (int(subset_df['mni_x']), int(subset_df['mni_y']), int(subset_df['mni_z']))
        tms_opt.subpath = os.path.join(CHARM_PATH, f'sub-{subject}', f'ses-{session}', f'm2m_sub-{subject}_ses-{session}')
        tms_opt.fnamecoil ='/home/zaineb/simnibs/resources/coil_models/Drakaki_BrainStim_2022/MagVenture_Cool-B65.ccd'
        if optim_orientation:
            tms_opt.pathfem = os.path.join(SIMNIBS_PATH,f'sub-{subject}/ses-{session}',
                                           f'sub-{subject}_ses-{session}_tmsoptim')
            os.makedirs(tms_opt.pathfem, exist_ok=True)
            tms_opt.target = mni2subject_coords(mni_coords, tms_opt.subpath)
            tms_opt.method = 'ADM'
        else: 
            tms_opt.pathfem = os.path.join(SIMNIBS_PATH,f'sub-{subject}/ses-{session}',
                                           f'sub-{subject}_ses-{session}_tmsoptim_toFront')
            os.makedirs(tms_opt.pathfem, exist_ok=True)
            tms_opt.target = mni2subject_coords(mni_coords, tms_opt.subpath)
            tms_opt.search_angle = 0
            tms_opt.pos_ydir = mni2subject_coords(toward_front, tms_opt.subpath)        
        print('Target:', tms_opt.target, 'End Target')
        opt_pos=tms_opt.run()
        fn = os.path.join(tms_opt.pathfem, f'sub-{subject}_ses-{session}_opt_pos')
        localite().write(np.squeeze(opt_pos), fn)
