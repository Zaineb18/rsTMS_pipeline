from rsTMS_pipeline.data_loading.params import *
import glob
import nibabel as nib
from nilearn.image import mean_img 

# ==========================
# Utility functions that return lists of NIfTI file paths at different 
# stages of the pipeline, using glob to find files matching BIDS naming conventions.

# Author: Zaineb Amor
# ==========================


def load_sourcedata(SOURCE_PATH, subj, ses):
    RFUNC_PATH = glob.glob(os.path.join(SOURCE_PATH, f'sub-{subj}', f'ses-{ses}', 'func', f'sub-{subj}_ses-{ses}*_bold.nii*'))
    RFMAP_PATH = glob.glob(os.path.join(SOURCE_PATH, f'sub-{subj}', f'ses-{ses}', 'fmap', f'sub-{subj}_ses-{ses}_epi.nii*'))
    return(RFUNC_PATH, RFMAP_PATH)

def load_rawdata(RAW_PATH, subj, ses):
    RFUNC_PATH = glob.glob(os.path.join(RAW_PATH, f'sub-{subj}', f'ses-{ses}', 'func', f'sub-{subj}_ses-{ses}*_bold.nii*'))
    RFMAP_PATH = glob.glob(os.path.join(RAW_PATH, f'sub-{subj}', f'ses-{ses}', 'fmap', f'sub-{subj}_ses-{ses}_*_epi.nii*'))
    return(RFUNC_PATH, RFMAP_PATH)

def load_trimmeddata(SOURCE_PATH, subj, ses):
    RFUNC_PATH = glob.glob(os.path.join(SOURCE_PATH, f'sub-{subj:02}', f'ses-{ses}', 'func', f'sub-{subj:02}_ses-{ses}*_acq-trimmed*_bold.nii*'))
    RFMAP_PATH = glob.glob(os.path.join(SOURCE_PATH, f'sub-{subj:02}', f'ses-{ses}', 'fmap', f'sub-{subj:02}_ses-{ses}*_acq-trimmed*_epi.nii*'))
    return(RFUNC_PATH, RFMAP_PATH)

def load_fmriprepdata(FMRIPREP_PATH, subj, ses, space):
    FUNC_PATH = sorted(glob.glob(os.path.join(FMRIPREP_PATH, f'sub-{subj:02}', f'ses-{ses}', 'func', f'*space-{space}*bold.nii.gz')))
    MASK_PATH = sorted(glob.glob(os.path.join(FMRIPREP_PATH, f'sub-{subj:02}', f'ses-{ses}', 'func', f'*space-{space}*brain_mask.nii.gz')))
    confounds_file = sorted(glob.glob(os.path.join(FMRIPREP_PATH, f'sub-{subj:02}', f'ses-{ses}', 'func', f"*_desc-confounds_timeseries.tsv")))

    ANAT_PATH = glob.glob(os.path.join(FMRIPREP_PATH, f'sub-{subj:02}', f'ses-{ses}', 'anat', f'*space-{space}*_T1w.nii.gz'))
    GM_PATH = glob.glob(os.path.join(FMRIPREP_PATH, f'sub-{subj:02}', f'ses-{ses}', 'anat', f'*space-{space}*_label-GM_probseg.nii.gz'))
    return(FUNC_PATH, MASK_PATH, confounds_file, ANAT_PATH, GM_PATH)
