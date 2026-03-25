from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
from rsTMS_pipeline.preproc.preproc_utils import *
import glob
import os
import shutil

# ==========================
# Organizing Raw Functional and Fieldmap Data
#
# Author: Zaineb Amor
#
# This section handles the following steps for each subject and session:
#
# 1. **Load Raw Data**
#    - Functional (BOLD) and fieldmap (FMAP) files are loaded using the `load_rawdata` utility.
#    - Files are sorted by run for consistent ordering.
#
# 2. **Prepare Destination Folders**
#    - Destination directories for non-trimmed functional and fieldmap data are created:
#        * `nontrimmed_data/func`
#        * `nontrimmed_data/fmap`
#    - Existing directories are reused if they already exist.
#
# 3. **Move Files**
#    - Each functional (BOLD) file is moved to `trimmed_data/func`.
#    - Each fieldmap (FMAP) file is moved to `trimmed_data/fmap`.
#    - Progress is printed for verification.
#
# Notes:
#    - This step is useful for organizing raw, unprocessed data before any trimming or preprocessing.
#    - File names and structure follow BIDS conventions.
#    - This script should only be used if AP/PA acquisitions exist for the subject/session.
# ==========================

for subj in subjects: 
    for ses in sessions: 
        RFUNC_PATH, RFMAP_PATH = load_trimmeddata(SOURCE_PATH, 1, ses)    
        #bold_files = sort_by_run(RFUNC_PATH)
        #fmap_files = sort_by_run(RFMAP_PATH)
        bold_files = RFUNC_PATH
        fmap_files = RFMAP_PATH

        print("Sorted BOLD:", bold_files)    
        print("Sorted FMAP:", fmap_files)   

        dest_func_dir = os.path.join(RAW_PATH, f'sub-{subj:02}', f'ses-{ses}', 'func')
        dest_fmap_dir = os.path.join(RAW_PATH, f'sub-{subj:02}', f'ses-{ses}', 'fmap')
        print(dest_func_dir, dest_fmap_dir)
        os.makedirs(dest_func_dir, exist_ok=True)
        os.makedirs(dest_fmap_dir, exist_ok=True)

        for bold_file in bold_files:
            dest_bold_file = os.path.join(dest_func_dir, os.path.basename(bold_file).replace('_acq-trimmed',''))
            shutil.move(bold_file, dest_bold_file)
            print(f"Moved {bold_file} -> {dest_bold_file}")            
            json_path = bold_file.replace('nii', 'json')
            dest_json_path = dest_bold_file.replace('nii', 'json')
            shutil.move(json_path, dest_json_path)
            print(f"Moved {json_path} -> {dest_json_path}")            

        for fmap_file in fmap_files:
            dest_fmap_file = os.path.join(dest_fmap_dir, os.path.basename(fmap_file))
            shutil.move(fmap_file, dest_fmap_file)
            print(f"Moved {fmap_file} -> {dest_fmap_file}")
            json_path = fmap_file.replace('nii', 'json')
            dest_json_path = dest_fmap_file.replace('nii', 'json')
            shutil.move(json_path, dest_json_path)            
            print(f"Moved {json_path} -> {dest_json_path}")                        
        
        source_anat_dir = os.path.join(SOURCE_PATH, f'sub-{subj:02}', f'ses-{ses}', 'anat')
        dest_anat_dir = os.path.join(RAW_PATH, f'sub-{subj:02}', f'ses-{ses}', 'anat')    
        os.makedirs(dest_anat_dir, exist_ok=True)
        for root, dirs, files in os.walk(source_anat_dir):
            rel_path = os.path.relpath(root, source_anat_dir)
            dest_root = os.path.join(dest_anat_dir, rel_path)
            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(dest_root, file)
                shutil.copy2(src_file, dst_file)