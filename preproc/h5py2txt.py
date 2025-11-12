from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
from rsTMS_pipeline.preproc.preproc_utils import *
import glob
import os

# ==========================
# Extract and Save Affine Transforms from fMRIPREP H5 Files
#
# Authors: Zaineb Amor, Guillaume Goudriet
#
# For each subject and session:
#   - Locate the H5 file that stores the transformation from MNI space to the subject's T1w anatomical space.
#   - Open the H5 file using h5py and extract:
#       * TransformParameters: contains the rotation matrix and translation vector.
#       * TransformFixedParameters: contains the center of rotation.
#   - Reshape the first 9 parameters into a 3x3 rotation matrix.
#   - Extract the translation vector (parameters 10-12) and the center.
#   - Initialize a MatrixOffsetTransformBase object with the matrix, translation, and center.
#   - Compute the offset and generate the full affine transformation matrix.
#   - Print all intermediate results for verification:
#       * Rotation matrix
#       * Translation vector
#       * Center
#       * Offset
#       * Affine matrix
#   - Check if the output folder exists in TRANSFORM_PATH; if not, create it.
#   - Save the affine matrix as a .txt file (converted from .h5) for downstream use.
#
# Note:
#   - This step allows the affine transform from template (MNI) to individual anatomical space to be exported in a standard format.
#   - The saved affine matrices can be used for aligning TMS targets or other ROI transformations.
# ==========================

for subj in subjects:
    for ses in sessions: 
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