from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
from rsTMS_pipeline.preproc.preproc_utils import *
import glob
import nibabel as nib
from nilearn.image import mean_img,load_img, index_img
import os
import shutil

# ==========================
# Remove First Scans from Functional and Fieldmap NIfTI Data
#
# Author: Zaineb Amor
#
# This script removes first volumes (non-steady-state volumes) from the beginning
# of BOLD and fieldmap (fmap) acquisitions for each subject and session.
#
# Background:
#   At the start of an fMRI acquisition, the MRI signal has not yet reached
#   steady state. The first few volumes are therefore discarded
#   before further preprocessing.
#
# Steps performed for each subject/session:
#
# 1. Load raw BOLD and fmap NIfTI file paths via `load_rawdata`.
#    If multiple runs are detected (run-XX label in filenames), files are
#    sorted by run number for consistent ordering.
#
# 2. Trim BOLD files:
#    - Drop the first 10 volumes using index_img(img, slice(10, None)).
#    - Overwrite the original file with the trimmed image.
#
# 3. Trim fieldmap files:
#    - Extract a single representative volume (volume index 10, i.e. the 11th)
#      from each fieldmap image using index_img(img, 10).
#    - Overwrite the original file with this single-volume image.
#    - A single volume is used here because fmaps are later averaged or used
#      directly as a static reference during distortion correction.
#
# Notes:
#   - JSON sidecar files are not modified by this script.
#   - Run this script before ap_pa.py.
# ==========================

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
                    
        print("Sorted BOLD:", bold_files)    
        print("Sorted FMAP:", fmap_files)        

        for path in bold_files:
            img = load_img(path) 
            trimmed_img = index_img(img, slice(10, None))  # Drop first 10 volumes
            #new_path = path.replace('acq-full', 'acq-trimmed') # Create new path by replacing 'acq_full' with 'acq_trimmed'
            #json_path = path.replace('nii', 'json')
            #newjson_path = json_path.replace('acq-full', 'acq-trimmed') # Create new path by replacing 'acq_full' with 'acq_trimmed'
            #shutil.copy(json_path,newjson_path)
            #print(f"Json file copied and renamed: {json_path} → {newjson_path}")
            #add_ignore_suffix(json_path)
            #os.makedirs(os.path.dirname(new_path), exist_ok=True)
            trimmed_img.to_filename(path)
            print(f"Saved trimmed BOLD to: {path}")
         
        for path in fmap_files:
            img = load_img(path) 
            #trimmed_img = index_img(img, slice(10, None))  # Drop first 10 volumes
            #json_path = path.replace('nii', 'json')
            #newjson_path = json_path.replace('acq-full', 'acq-trimmed') # Create new path by replacing 'acq_full' with 'acq_trimmed'
            #shutil.copy(json_path,newjson_path)
            #print(f"Json file copied and renamed: {json_path} → {newjson_path}")
            #add_ignore_suffix(json_path)
            #avg_img = mean_img(trimmed_img)  # Drop first 10 volumes
            trimmed_img = index_img(img, 10)
            #new_path = path.replace('acq-full', 'acq-trimmed') # Create new path by replacing 'acq_full' with 'acq_trimmed'
            #os.makedirs(os.path.dirname(new_path), exist_ok=True)
            trimmed_img.to_filename(path)
            print(f"Saved 11'th frame of FMAP to: {path}")            

