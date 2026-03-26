from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
from rsTMS_pipeline.preproc.preproc_utils import *
from nilearn import image
from nilearn.interfaces.fmriprep import load_confounds
import os

# ==========================
# Denoise Preprocessed fMRI Data Using fMRIPrep Confounds
#
# Authors: Zaineb Amor
#
# Context:
#   After fMRIPrep preprocessing, BOLD images still contain noise from head
#   motion and physiological sources (white matter, CSF signals). This script
#   removes those artifacts by regressing out confound regressors generated
#   by fMRIPrep, producing cleaned BOLD images ready for functional
#   connectivity analyses or other downstream processing.
#
# This script loops over all subjects and sessions. For each, it:
#
# --- Step 1: Load fMRIPrep outputs ---
#
#   Calls load_fmriprepdata() to retrieve the paths to all relevant files
#   for a given subject, session, and MNI space:
#     - BOLD functional image(s)
#     - Brain mask(s)
#     - Confounds TSV sidecar(s)
#     - Preprocessed T1w anatomical image
#     - Grey matter probability map
#
# --- Step 2: Detect and handle multi-run sessions ---
#
#   Checks whether the BOLD filenames contain a 'run-XX' entity. If so,
#   BOLD, mask, and confounds file lists are sorted by run number using
#   sort_by_run(), ensuring that each BOLD run is paired with its
#   corresponding mask and confounds file.
#   Single-run sessions are handled transparently: the file lists each
#   contain one element and the inner loop iterates once.
#
# --- Step 3: Denoise each run ---
#
#   For each (BOLD, mask, confounds) triplet:
#     1. Print resolved file paths for logging and manual verification.
#     2. Call clean_bold() (defined in preproc_utils.py), which:
#          a. Loads confound regressors from the fMRIPrep TSV via
#             load_confounds, using motion parameters (6 params +
#             temporal derivatives) and WM/CSF mean signals.
#          b. Imputes NaN values in the confounds matrix with 0.
#             Motion derivative confounds are undefined at t=0 (no prior
#             timepoint), producing a NaN in the first row. Filling with 0
#             means the regressor contributes nothing at that timepoint,
#             which is the correct neutral assumption. This is required
#             because scipy's QR decomposition inside clean_img cannot
#             handle non-finite values.
#          c. Cleans the BOLD image by regressing out confounds, applying
#             linear detrending to remove slow scanner drift, and masking
#             to in-brain voxels. Standardization is disabled to preserve
#             the original BOLD signal scale.
#          d. Returns the cleaned image, its mean (for QC), the sample
#             mask (indices of retained timepoints), and the imputed
#             confounds DataFrame.
#     3. Save the cleaned BOLD image to disk, replacing "preproc_bold"
#        with "preproc_bold_cleaned" in the filename to maintain
#        BIDS-like naming conventions.
#
# Notes:
#   - Run fMRIPrep before this script. The confounds TSV sidecar must
#     exist alongside the BOLD NIfTI in the fMRIPrep derivatives folder.
#   - load_fmriprepdata() resolves glob patterns internally and returns
#     concrete file paths; no glob handling is needed here.
#   - The TR is passed to clean_bold() for reference (default: 1.09 s)
#     and is reserved for future use such as temporal filtering.
#   - The grey matter map (GM_PATH) is loaded but not used in this script;
#     it is retrieved here for consistency with other preprocessing steps.
# ==========================

for subj in subjects:
    for ses in sessions:
        FUNC_PATH, MASK_PATH, CONFOUNDS_PATH, ANAT_PATH, GM_PATH = load_fmriprepdata(FMRIPREP_PATH, 
                                                        subj, ses, space)
        bold_files = FUNC_PATH
        mask_files = MASK_PATH
        confounds_files = CONFOUNDS_PATH
        anat_files = ANAT_PATH         
        # Detect whether run labels exist in filenames
        func_has_runs = any(re.search(r'run-(\d+)', f) for f in bold_files)
        multi_run = func_has_runs
        if multi_run:
            bold_files = sort_by_run(bold_files)
            mask_files = sort_by_run(mask_files)
            confounds_files = sort_by_run(confounds_files)
        anat = image.load_img(anat_files)
        for func_f, mask_f, confounds_f in zip(bold_files, mask_files, confounds_files):
            print(func_f,'\n', confounds_f, '\n', mask_f)
            clean_func, mean_func, sample_mask, confounds = clean_bold(func_f,
                                                                   confounds_f,mask_f, tr=1.09)
            cfunc_f=func_f.replace("preproc_bold","preproc_bold_cleaned")
            clean_func.to_filename(cfunc_f)



