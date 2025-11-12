from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
from rsTMS_pipeline.preproc.preproc_utils import *
import glob
import nibabel as nib
from nilearn.image import mean_img,load_img, index_img
import os
import shutil

# ==========================
# Trimming Functional and Fieldmap NIfTI Data
#
# Author: Zaineb Amor
#
# This section handles the following steps for each subject and session:
#
# 1. **Load Raw Data**
#    - Functional (BOLD) and fieldmap (FMAP) files are loaded using the `load_rawdata` utility.
#    - Files are sorted by run for consistent ordering.
#
# 2. **Trim Functional (BOLD) Data**
#    - For each BOLD file:
#        * Load the NIfTI image.
#        * Remove the first 10 volumes to discard potential scanner artifacts (`index_img(img, slice(10, None))`).
#        * Create a new file path replacing 'acq-full' with 'acq-trimmed'.
#        * Copy and rename the associated JSON file to match the trimmed NIfTI.
#        * Apply `add_ignore_suffix` to the original JSON file (marks it as ignored in further processing).
#        * Save the trimmed NIfTI image to the new path.
#        * Print status messages for tracking progress.
#
# 3. **Trim Fieldmap (FMAP) Data**
#    - For each FMAP file:
#        * Load the NIfTI image.
#        * Remove the first 10 volumes.
#        * Create a new file path replacing 'acq-full' with 'acq-trimmed'.
#        * Copy and rename the associated JSON file to match the trimmed NIfTI.
#        * Apply `add_ignore_suffix` to the original JSON file.
#        * Compute the mean image across the trimmed volumes.
#        * Save the averaged, trimmed FMAP image to the new path.
#        * Print status messages for tracking progress.
#
# Notes:
#    - Trimming the first 10 volumes helps remove initial scanner instability artifacts.
#    - JSON files are copied and renamed to maintain BIDS compliance with the new trimmed data.
#    - File naming follows BIDS conventions (e.g., 'acq-full' → 'acq-trimmed').
# ==========================

for subj in subjects: 
    for ses in sessions: 
        RFUNC_PATH, RFMAP_PATH = load_rawdata(RAW_PATH, 'P3', ses)    
        bold_files = sort_by_run(RFUNC_PATH)
        fmap_files = sort_by_run(RFMAP_PATH)
        print("Sorted BOLD:", bold_files)    
        print("Sorted FMAP:", fmap_files)        

        for path in bold_files:
            img = load_img(path) 

            trimmed_img = index_img(img, slice(10, None))  # Drop first 10 volumes
            new_path = path.replace('acq-full', 'acq-trimmed') # Create new path by replacing 'acq_full' with 'acq_trimmed'

            json_path = path.replace('nii', 'json')
            newjson_path = json_path.replace('acq-full', 'acq-trimmed') # Create new path by replacing 'acq_full' with 'acq_trimmed'
            shutil.copy(json_path,newjson_path)
            print(f"Json file copied and renamed: {json_path} → {newjson_path}")
            add_ignore_suffix(json_path)
            
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            trimmed_img.to_filename(new_path)
            print(f"Saved trimmed BOLD to: {new_path}")
         

        for path in fmap_files:
            img = load_img(path) 
            trimmed_img = index_img(img, slice(10, None))  # Drop first 10 volumes

            json_path = path.replace('nii', 'json')
            newjson_path = json_path.replace('acq-full', 'acq-trimmed') # Create new path by replacing 'acq_full' with 'acq_trimmed'
            shutil.copy(json_path,newjson_path)
            print(f"Json file copied and renamed: {json_path} → {newjson_path}")
            add_ignore_suffix(json_path)
            
            avg_img = mean_img(trimmed_img)  # Drop first 10 volumes
            new_path = path.replace('acq-full', 'acq-trimmed') # Create new path by replacing 'acq_full' with 'acq_trimmed'
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            avg_img.to_filename(new_path)
            print(f"Saved trimmed and averaged FMAP to: {new_path}")            

