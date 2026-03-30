from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
import os
from simnibs import opt_struct, mni2subject_coords
from simnibs import localite
import numpy as np
import pandas as pd

# ==========================
# SimNIBS TMS Coil Position Optimisation for Individualized Targeting
#
# Author: Zaineb Amor & Guillaume Coudriet
#
# Context:
#   Once the individualized target MNI coordinate has been identified,
#   the optimal TMS coil position and orientation must be computed to maximally
#   stimulate that cortical target given the individual subject's head anatomy.
#   This script uses SimNIBS TMSoptimize to solve that problem, using the
#   CHARM head model built from each subject's fMRIPrep T1w image.
#
#   The coil used is the MagVenture Cool-B65 (figure-of-eight), a standard
#   clinical coil used in MDD TMS protocols.
#
# This script loops over all subjects and sessions. For each, it:
#
# --- Step 1: Load individualized target coordinate ---
#
#   Reads the targeting results TSV from:
#     RES_PATH/sub-{subject}/ses-{session}/
#       sub-{subject}_ses-{session}_targeting-results.csv
#   Filters to the row where:
#     - tissue == 'GM mask'   (most anatomically precise restriction)
#     - stat   == 'Fisher Z'  (most statistically appropriate metric)
#   Extracts mni_x, mni_y, mni_z as integer MNI coordinates.
#
# --- Step 2: Configure SimNIBS TMSoptimize ---
#
#   Sets up a TMSoptimize object with the following fields:
#   subpath   — path to the subject's CHARM head model directory
#               (m2m_sub-{subject}_ses-{session}), built by charmtms_bash.sh
#   pathfem   — output directory for the FEM simulation results
#               (created if it does not exist)
#   fnamecoil — path to the MagVenture Cool-B65 coil definition file (.ccd),
#               located in the SimNIBS coil model library
#   target    — individualized cortical target in subject (T1w) space,
#               converted from MNI to subject coordinates via
#               mni2subject_coords(), which applies the inverse MNI→T1w
#               transform stored in the CHARM head model
#   method    — 'ADM' (Auxiliary Dipole Method), SimNIBS's recommended
#               fast optimisation method for single-target coil placement
#
# --- Step 3: Run coil position optimisation ---
#
#   Calls tms_opt.run(), which:
#     1. Loads the CHARM head model mesh
#     2. Runs ADM optimisation to find the coil position and orientation
#        that maximises the electric field magnitude at the target coordinate
#     3. Returns opt_pos: the optimal 4×4 coil-to-head affine matrix
#        (position + orientation)
#
# --- Step 4: Export coil position for neuronavigation ---
#
#   Saves the optimal coil position to a Localite TMS Navigator-compatible
#   file via localite().write(), at:
#     SIMNIBS_PATH/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_tmsoptim*/
#       sub-{subject}_ses-{session}_opt_pos
#   The Localite format encodes the 4×4 coil matrix and can be loaded
#   directly into the Localite TMS Navigator neuronavigation system
#   for coil placement during the TMS session.
#
# Notes:
#   - Run charmtms_bash.sh before this script. 
#   - The targeting results CSV must exist in RES_PATH.
#   - The coil file path is currently hardcoded to the MagVenture Cool-B65.
#     Update fnamecoil if a different coil is used.
#   - tms_opt is instantiated once outside the loop and reused across
#     subjects and sessions. Fields are overwritten at each iteration.
#   - mni2subject_coords() requires the CHARM m2m directory to resolve
#     the MNI→T1w transform. Ensure the correct m2m path is set before
#     calling it.
#   - opt_pos is squeezed from shape (1, 4, 4) to (4, 4) before writing,
#     as localite().write() expects a 2D matrix.
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
