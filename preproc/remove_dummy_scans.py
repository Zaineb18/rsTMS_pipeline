from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
from rsTMS_pipeline.preproc.preproc_utils import *

import glob
import nibabel as nib
from nilearn.image import mean_img,load_img, index_img
import os
import shutil

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

