import re
import os, glob, h5py
from nilearn.image import mean_img, load_img, clean_img,math_img,new_img_like,resample_to_img
from nilearn.interfaces.fmriprep import load_confounds
from nilearn.maskers import NiftiSpheresMasker,NiftiMasker
import numpy as np
import nibabel as nib
from scipy.signal import detrend
from scipy.stats import pearsonr
from nibabel.affines import apply_affine
from nilearn import image
from rsTMS_pipeline.data_loading.params import *
import json5, json


# Fields that were present in the original (pre-anonymisation) JSON sidecars
# but are missing after DICOM conversion. These are required by fMRIPrep for
# susceptibility distortion correction (SDC).
# !! Fill in the 0.0 placeholders with the correct scanner values before
#    running fMRIPrep !!
MISSING_FIELDS = {
    #"PhaseEncodingPolarityGE":       "Flipped",
    #"MultibandAccelerationFactor":    0,
    #"ParallelReductionFactorInPlane": 0,
    "EffectiveEchoSpacing":           0.000312,
    "TotalReadoutTime":               0.024648,
    #"PhaseEncodingDirection":         "j",   # replaces PhaseEncodingAxis
}

def patch_json(json_path, is_ap=False):
    """
    Patch a JSON sidecar (BOLD, AP fmap, or PA fmap) with fields that were
    present in the original acquisition but are missing after DICOM conversion:
      - Renames 'PhaseEncodingAxis' → 'PhaseEncodingDirection', preserving the value.
        For the AP fmap (is_ap=True), the value is set to 'j-' regardless of the
        original, since AP is the opposite phase-encoding direction to PA/BOLD ('j').
      - Adds any key from MISSING_FIELDS that is absent from the file.
    Fill in the 0.0 placeholders with the correct scanner values before
    running fMRIPrep.
    """
    with open(json_path, 'r') as f:
        data = json5.load(f)

    changed = False

    # Rename PhaseEncodingAxis → PhaseEncodingDirection
    # PA : keep original value ('j')
    # AP/BOLD:        always set to 'j-' (opposite direction)
    if "PhaseEncodingAxis" in data or "PhaseEncodingDirection" in data:
        if "PhaseEncodingAxis" in data:
            val = data.pop("PhaseEncodingAxis")
        else:
            val = data.pop("PhaseEncodingDirection")
        data["PhaseEncodingDirection"] = "j-" if is_ap else val
        print(f"  Set PhaseEncodingDirection: {data['PhaseEncodingDirection']}")
        changed = True

    # Inject missing fields
    for field, value in MISSING_FIELDS.items():
        if field not in data:
            data[field] = value
            print(f"  Added: {field} = {value}")
            changed = True

    if changed:
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"  Patched: {json_path}")
    else:
        print(f"  No changes needed: {json_path}")

def extract_runs(file_list):
    runs = set()
    for f in file_list:
        match = re.search(r'run-(\d+)', f)
        if match:
            runs.add(f"run-{match.group(1)}")
    return sorted(runs)

def sort_by_run(files):
    return sorted(files, key=lambda x: int(re.search(r'run-(\d+)', x).group(1)))

def add_ignore_suffix(file_path):
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return
    new_path = file_path + '.ignore'
    os.rename(file_path, new_path)
    print(f"Renamed:\n  {file_path}\n→ {new_path}")

def clean_bold(func_f,confounds_f,mask_f, tr=1.09):
    confounds,sample_mask=load_confounds(func_f,strategy=("motion","wm_csf"),
                                                 motion="derivatives")
    func_cleaned=image.clean_img(func_f,confounds=confounds,sample_mask=sample_mask,
                                         mask_img=mask_f,standardize=False, detrend=False)
    #func_cleaned = image.clean_img(
    #    func_f,
    #    confounds=confounds,
    #    sample_mask=sample_mask,
    #    mask_img=mask_f,
    #    standardize="zscore_sample",  # normalize voxel variance
    #    detrend=False,                 # remove residual drift
        #high_pass=0.01,               # } bandpass — requires t_r
        #low_pass=0.1,                 # }
    #    t_r=tr                        # pass tr you already have
    #)
    mean_func=image.mean_img(func_cleaned)
    return(func_cleaned, mean_func, sample_mask, confounds)  

def h5txt(FMRIPREP_PATH, TRANSFORM_PATH, subj, ses):
    transform_file = glob.glob(os.path.join(FMRIPREP_PATH, f'sub-{subj:02}',f'ses-{ses}', 'anat', "*from-MNI152NLin2009cAsym_to-T1w_mode-image_xfm.h5"), recursive=True)[0]
    print(transform_file)
    f = h5py.File(transform_file, 'r')
    transform_parameters = f['TransformGroup']['2']['TransformParameters']
    fixed_parameters = f['TransformGroup']['2']['TransformFixedParameters']
    matrix=np.reshape(transform_parameters[:9], (3, 3))
    print(f'Matrix = \n{matrix}\n')
    translation=transform_parameters[9:12]
    print(f'Translation vector = \n{translation}\n')
    center=fixed_parameters[()]
    print(f'Center = \n{center}\n')
    transform = MatrixOffsetTransformBase(matrix, translation, center)
    transform.compute_offset()
    print(f'Offset = \n{transform.offset}\n')
    transform.generate_affine_matrix()
    print(f'Affine matrix = \n{transform.affine_matrix}\n')
    if not os.path.exists(os.path.join(TRANSFORM_PATH, f'sub-{subj:02}',f'ses-{ses}')):
        print(f"Folder '{os.path.join(TRANSFORM_PATH, f'sub-{subj:02}',f'ses-{ses}')}' does not exist. Creating it...")
        os.makedirs(os.path.join(TRANSFORM_PATH, f'sub-{subj:02}',f'ses-{ses}'))
    else:
        print(f"Folder '{os.path.join(TRANSFORM_PATH, f'sub-{subj:02}',f'ses-{ses}')}' already exists.") 
        np.savetxt(os.path.join(os.path.join(TRANSFORM_PATH, f'sub-{subj:02}',f'ses-{ses}'),
                                os.path.basename(transform_file).replace('_ses-pre','').replace('h5','txt')),transform.affine_matrix, delimiter=' ')


class MatrixOffsetTransformBase:
    def __init__(self, matrix, translation, center):
        self.matrix = np.array(matrix)
        self.translation = np.array(translation)
        self.center = np.array(center)
        self.offset = np.zeros_like(self.center)
        self.affine_matrix = np.eye(4)


    def compute_offset(self):
        self.offset = self.translation + self.center - self.matrix.dot(self.center)

    def generate_affine_matrix(self):

        self.affine_matrix[:3, :3] = self.matrix
        self.affine_matrix[:3, 3] = self.offset
        self.affine_matrix *= change_from_LPS_to_RAS

