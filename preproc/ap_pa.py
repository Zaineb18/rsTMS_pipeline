from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
from rsTMS_pipeline.preproc.preproc_utils import *
import json
import glob
import nibabel as nib
from nilearn.image import mean_img,load_img, index_img
import os
import shutil
import json5

# ==========================
# Generate AP Fieldmaps and Set IntendedFor in Fieldmap JSON Sidecars
#
# Author: Zaineb Amor
#
# Context:
#   Distortion correction in fMRI requires a pair of fieldmaps acquired in
#   opposite phase-encoding directions: AP (anterior-posterior) and PA
#   (posterior-anterior). When only PA fieldmaps are acquired alongside BOLD
#   data, an AP fieldmap can be derived by extracting a representative volume
#   directly from the BOLD image. This script automates that process and
#   ensures BIDS-compliant JSON sidecar linkage.
#
# This script runs two sequential loops over all subjects and sessions:
#
# --- Loop 1: Generate AP NIfTI and JSON files ---
#
#   For each BOLD / PA-fmap pair:
#     1. Load the trimmed BOLD image (output of remove_dummy_scans.py).
#     2. Extract volume at index 1 as the AP fieldmap reference.
#     3. Save the extracted volume as a new NIfTI file with 'dir-AP' in the
#        filename (derived by replacing 'dir-PA' in the fmap path).
#     4. Copy the BOLD JSON sidecar and rename it to match the new AP fmap.
#     5. Patch all three JSON sidecars (BOLD, AP, PA) with fields that were
#        present in the original acquisition but lost during DICOM conversion:
#          - Renames 'PhaseEncodingAxis' → 'PhaseEncodingDirection', preserving the value
#          - Injects MISSING_FIELDS (EffectiveEchoSpacing, TotalReadoutTime, etc.)
#        Fill in the 0.0 placeholders in MISSING_FIELDS with correct scanner
#        values before running fMRIPrep.
#
#   Supports both single-run and multi-run sessions.
#
# --- Loop 2: Set IntendedFor in all fieldmap JSON sidecars ---
#
#   For each fmap file (PA and newly created AP):
#     1. Identify the corresponding BOLD file.
#     2. Compute the BIDS-compliant relative path from the subject directory.
#     3. Write this path into the 'IntendedFor' field of the fmap JSON sidecar.
#
# Notes:
#   - Run remove_dummy_scans.py before this script.
#   - json5 is used when reading JSON sidecars to tolerate trailing commas or
#     other minor formatting issues in scanner-exported files.
#   - The IntendedFor path is relative to the subject directory, following
#     the BIDS specification (e.g. ses-1/func/filename.nii.gz).
# ==========================

 
# -----------------------------------------------------------------------
# Loop 1: Generate AP fieldmap NIfTI and JSON files from BOLD data
#         + patch PA fmap JSON with missing fields
# -----------------------------------------------------------------------
for subj in subjects: 
    for ses in sessions: 
        RFUNC_PATH, RFMAP_PATH = load_rawdata(RAW_PATH, subj, ses)    
        bold_files = RFUNC_PATH
        fmap_files = RFMAP_PATH
        # Detect whether run labels exist in filenames
        func_has_runs = any(re.search(r'run-(\d+)', f) for f in bold_files)
        fmap_has_runs = any(re.search(r'run-(\d+)', f) for f in fmap_files)
        multi_run = func_has_runs and fmap_has_runs
        if multi_run:
            bold_files = sort_by_run(bold_files)
            fmap_files = sort_by_run(fmap_files)
            
        for bold_file, fmap_file in zip(bold_files, fmap_files):
            print(f"BOLD: {bold_file}")
            print(f"FMAP: {fmap_file}")
            trimmed_img = load_img(bold_file)
            pa_img = index_img(trimmed_img, 1)
            pa_path = fmap_file.replace('dir-PA', 'dir-AP') 
            os.makedirs(os.path.dirname(pa_path), exist_ok=True)
            pa_img.to_filename(pa_path)
            
            # --- Copy BOLD JSON as AP fmap JSON ---
            jsonb_path  = bold_file.replace('nii.gz', 'json')
            jsonpa_path = fmap_file.replace('nii.gz', 'json')
            jsonap_path = jsonpa_path.replace('dir-PA', 'dir-AP')
            shutil.copy(jsonb_path, jsonap_path)
            print(f"  JSON copied and renamed: {jsonb_path} → {jsonap_path}")            
            
            # --- Patch PA, AP, and BOLD JSON sidecars with missing fields ---
            # All three use the BOLD JSON as the reference source for missing fields,
            # since it is the most complete sidecar produced by dcm2niix.
            # --- Patch BOLD, AP, and PA JSON sidecars ---
            # --- Patch BOLD, AP, and PA JSON sidecars ---
            for label, json_path, is_ap in [("BOLD",    jsonb_path,  True),
                                               ("AP fmap", jsonap_path, True),
                                               ("PA fmap", jsonpa_path, False)]:
                print(f"  Patching {label} JSON: {json_path}")
                patch_json(json_path, is_ap=is_ap)
                                            
# -----------------------------------------------------------------------
# Loop 2: Set IntendedFor field in all fieldmap JSON sidecars
# -----------------------------------------------------------------------
for subj in subjects:
    for ses in sessions:
        RFUNC_PATH, RFMAP_PATH = load_rawdata(RAW_PATH, subj, ses)
        bold_files = RFUNC_PATH
        fmap_files = RFMAP_PATH
        # Detect whether run labels exist in filenames
        func_has_runs = any(re.search(r'run-(\d+)', f) for f in bold_files)
        fmap_has_runs = any(re.search(r'run-(\d+)', f) for f in fmap_files)
        multi_run = func_has_runs and fmap_has_runs
        if multi_run:
            bold_files = sort_by_run(bold_files)
            fmap_files = sort_by_run(fmap_files)            
        subj_dir = os.path.join(RAW_PATH, f'sub-{subj}') 

        for fmap_file in fmap_files:
            if multi_run:
                fmap_run = re.search(r'run-(\d+)', fmap_file)
                if fmap_run is None:
                    print(f"Could not extract run number from {fmap_file}")
                    continue
                fmap_run = fmap_run.group(1)
                matching_func = None
                for bold_file in bold_files:
                    bold_run = re.search(r'run-(\d+)', bold_file)
                    if bold_run and bold_run.group(1) == fmap_run:
                        matching_func = os.path.relpath(bold_file, start=subj_dir)
                        break
                if matching_func is None:
                    print(f"No matching func file found for {fmap_file}")
                    continue
            else:
                if not bold_files:
                    print(f"No func files found for {fmap_file}")
                    continue
                matching_func = os.path.relpath(bold_files[0], start=subj_dir)

            fmap_json = fmap_file.replace('.nii.gz', '.json')
            print('FMAP', fmap_file, 'JSON', fmap_json)
            print('BOLD', matching_func)
            with open(fmap_json, 'r') as f:
                fmap_data = json5.load(f)                
            fmap_data['IntendedFor'] = [matching_func]
            with open(fmap_json, 'w') as f:
                json.dump(fmap_data, f, indent=4) 
                
                
                
