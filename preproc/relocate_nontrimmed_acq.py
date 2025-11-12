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
#    - Each functional (BOLD) file is moved to `nontrimmed_data/func`.
#    - Each fieldmap (FMAP) file is moved to `nontrimmed_data/fmap`.
#    - Progress is printed for verification.
#
# Notes:
#    - This step is useful for organizing raw, unprocessed data before any trimming or preprocessing.
#    - File names and structure follow BIDS conventions.
#    - This script should only be used if AP/PA acquisitions exist for the subject/session.
# ==========================

for subj in subjects: 
    for ses in sessions: 
        RFUNC_PATH, RFMAP_PATH = load_rawdata(RAW_PATH, 'P3', ses)    
        bold_files = sort_by_run(RFUNC_PATH)
        fmap_files = sort_by_run(RFMAP_PATH)
        print("Sorted BOLD:", bold_files)    
        print("Sorted FMAP:", fmap_files)   

        dest_func_dir = os.path.split('bold_files')[0]+f'nontrimmed_data/func'
        dest_fmap_dir = os.path.split('fmap_files')[0]+f'nontrimmed_data/fmap'
        print(dest_func_dir, dest_fmap_dir)
        os.makedirs(dest_func_dir, exist_ok=True)
        os.makedirs(dest_fmap_dir, exist_ok=True)

        for bold_file in bold_files:
            dest_bold_file = os.path.join(dest_func_dir, os.path.basename(bold_file))
            shutil.move(bold_file, dest_bold_file)
            print(f"Moved {bold_file} -> {dest_bold_file}")
        for fmap_file in fmap_files:
            dest_fmap_file = os.path.join(dest_fmap_dir, os.path.basename(fmap_file))
            shutil.move(fmap_file, dest_fmap_file)
            print(f"Moved {fmap_file} -> {dest_fmap_file}")
     
