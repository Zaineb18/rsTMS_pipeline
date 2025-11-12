from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
from rsTMS_pipeline.preproc.preproc_utils import *
import json
import glob
import nibabel as nib
from nilearn.image import mean_img,load_img, index_img
import os
import shutil

# ==========================
# Preparing and Linking NIfTI and JSON Files
#
# Author: Zaineb Amor
#
# This section handles the following steps for each subject and session:
#
# 1. **NIfTI Files**
#    - Load the trimmed functional (BOLD) and fieldmap (FMAP) data for the subject/session.
#    - Sort the BOLD and FMAP files by run.
#    - For each BOLD/FMAPP pair:
#        * Compute the mean image of the BOLD file.
#        * Generate a new AP-direction file from the PA-direction fieldmap and save the mean BOLD image there.
#        * Copy the BOLD JSON file, rename it to match the new AP fieldmap, and save it.
#    - This ensures that each fieldmap has a corresponding BOLD mean image and JSON metadata file.
#
# 2. **JSON Files**
#    - Match each fieldmap JSON file to its corresponding functional run.
#    - Update the fieldmap JSON with an 'IntendedFor' entry pointing to the matched BOLD file.
#    - Save the updated JSON with proper indentation for readability.
#
# Notes:
#    - This procedure ensures that the fieldmaps are correctly linked to the functional data they should correct.
#    - File naming follows BIDS conventions (e.g., 'run-01', 'dir-PA', 'dir-AP').
#    - This script should only be used if AP/PA acquisitions exist for the subject/session.
# ==========================

################################ nifti files
for subj in subjects: 
    for ses in sessions: 
        RFUNC_PATH, RFMAP_PATH = load_trimmeddata(RAW_PATH, 'P3', ses)    
        bold_files = sort_by_run(RFUNC_PATH)
        fmap_files = sort_by_run(RFMAP_PATH)
        print("Sorted BOLD:", bold_files)    
        print("Sorted FMAP:", fmap_files)        

        for bold_file, fmap_file in zip(bold_files, fmap_files):
            print(f"BOLD: {bold_file}")
            print(f"FMAP: {fmap_file}")

            trimmed_img = load_img(bold_file)
            avg_img = mean_img(trimmed_img)  
            pa_path = fmap_file.replace('dir-PA', 'dir-AP') 
            os.makedirs(os.path.dirname(pa_path), exist_ok=True)
            avg_img.to_filename(pa_path)

            jsonb_path = bold_file.replace('nii', 'json')
            jsonf_path = fmap_file.replace('nii', 'json')

            pajson_path = jsonf_path.replace('dir-PA', 'dir-AP') 
            shutil.copy(jsonb_path,pajson_path)
            print(f"Json file copied and renamed: {jsonb_path} → {pajson_path}")
            
#####################################json files
for subj in subjects: 
    for ses in sessions: 
        RFUNC_PATH, RFMAP_PATH = load_trimmeddata(RAW_PATH, 'P3', ses)    
        bold_files = sort_by_run(RFUNC_PATH)
        fmap_files = sort_by_run(RFMAP_PATH)
        for fmap_file in fmap_files:
            fmap_run = re.search(r'run-(\d+)', fmap_file).group(1)
            matching_func = None
            for bold_file in bold_files:
                bold_run = re.search(r'run-(\d+)', bold_file).group(1)
                if bold_run == fmap_run:
                    matching_func = os.path.relpath(bold_file, start=os.path.dirname(fmap_file))
                    break

            if matching_func is None:
                print(f"No matching func file found for {fmap_file}")
                continue
    
            fmap_json = fmap_file.replace('.nii', '.json')
            print('FMAP', fmap_file, 'JSON', fmap_json)
            print('BOLD', matching_func)

            with open(fmap_json, 'r') as f:
                fmap_data = json.load(f)
    
            fmap_data['IntendedFor'] = [matching_func]

            with open(fmap_json, 'w') as f:
                json.dump(fmap_data, f, indent=4) 
