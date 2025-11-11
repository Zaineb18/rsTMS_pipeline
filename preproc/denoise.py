from rsTMS_pipeline.data_loading.params import *
from nilearn import image, plotting
from nilearn.interfaces.fmriprep import load_confounds
import os

for subject in subjects:
    for session in sessions:

        ANAT_FILE = f'sub-{subject:02}_ses-{session}_space-MNI152NLin2009cAsym_desc-preproc_T1w.nii.gz'
        FUNC_FILE = f'sub-{subject:02}_ses-{session}_task-rs_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz' 
        MASK_FILE = f'sub-{subject:02}_ses-{session}_task-rs_space-MNI152NLin2009cAsym_desc-brain_mask.nii.gz'
        ANAT_PATH = os.path.join(FMRIPREP_PATH, f'sub-{subject:02}',f'ses-{session}', 'anat', ANAT_FILE)
        FUNC_PATH = os.path.join(FMRIPREP_PATH, f'sub-{subject:02}',f'ses-{session}', 'func', FUNC_FILE)
        MASK_PATH = os.path.join(FMRIPREP_PATH, f'sub-{subject:02}',f'ses-{session}', 'func', MASK_FILE)

        anat = image.load_img(ANAT_PATH)
        func = image.load_img(FUNC_PATH)
        mean_img=image.mean_img(func)
        mask = image.load_img(MASK_PATH)

        confounds,sample_mask=load_confounds(FUNC_PATH,strategy=("motion","wm_csf"),motion="derivatives")
        func_cleaned=image.clean_img(func,confounds=confounds,sample_mask=sample_mask,mask_img=mask,standardize=False,linear_detrend=True)
        cleaned_mean_img=image.mean_img(func_cleaned)
        CFUNC_PATH=FUNC_PATH.replace("preproc_bold","preproc_bold_cleaned")
        func_cleaned.to_filename(CFUNC_PATH)
