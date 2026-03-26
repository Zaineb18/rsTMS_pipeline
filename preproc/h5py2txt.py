from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
from rsTMS_pipeline.preproc.preproc_utils import *
import glob
import os

# ==========================
# Extract Affine Transforms from fMRIPrep H5 Files and Export as .txt
#
# Authors: Zaineb Amor, Guillaume Goudriet
#
# Context:
#   fMRIPrep stores spatial transformation parameters in HDF5 (.h5) files
#   following the ITK/ANTs convention. These transforms encode the mapping
#   from MNI152 template space back to each subject's native T1w anatomical
#   space. While .h5 files are natively consumed by ANTs, many downstream
#   tools (e.g. for TMS target localisation or ROI back-projection) require
#   the transform as a plain 4x4 affine matrix in a text file. This script
#   unpacks the ITK transform parameters, reconstructs the full affine
#   matrix, and exports it in that format.
#
# This script runs a single loop over all subjects and sessions:
#
# --- Loop: Extract and export the MNI-to-T1w affine for each subject ---
#
#   For each subject and session:
#     1. Locate the fMRIPrep-generated H5 file encoding the inverse
#        (MNI152NLin2009cAsym → T1w) transform using a glob pattern on
#        the keyword 'from-MNI152NLin2009cAsym_to-T1w_mode-image_xfm'.
#     2. Open the H5 file with h5py and read from TransformGroup/2:
#          - TransformParameters: flat array of 12 values encoding the
#            3x3 rotation/scaling matrix (indices 0–8) and the 3D
#            translation vector (indices 9–11).
#          - TransformFixedParameters: 3D center of rotation, stored
#            separately in ITK's MatrixOffsetTransformBase convention.
#     3. Reconstruct the ITK transform components:
#          - Reshape the first 9 parameters into a 3x3 matrix.
#          - Extract the translation vector (parameters 9–11).
#          - Read the center of rotation from the fixed parameters.
#     4. Instantiate a MatrixOffsetTransformBase object with the matrix,
#        translation, and center, then:
#          - Call compute_offset() to derive the effective translation
#            offset, which accounts for the center of rotation:
#            offset = translation + center - matrix @ center
#          - Call generate_affine_matrix() to assemble the full 4x4
#            homogeneous affine matrix from the matrix and offset.
#     5. Print all intermediate components (matrix, translation, center,
#        offset, affine matrix) for verification and debugging.
#     6. Ensure the subject/session output directory exists under
#        TRANSFORM_PATH, creating it if necessary.
#     7. Save the 4x4 affine matrix as a space-delimited .txt file.
#        The output filename is derived from the H5 filename by:
#          - Stripping the session suffix '_ses-pre' (protocol-specific
#            label not needed in the output).
#          - Replacing the '.h5' extension with '.txt'.
#
# Notes:
#   - This script must be run after fMRIPrep, which generates the H5
#     transform files in the anat/ subfolder of each subject's derivatives.
#   - Only TransformGroup/2 is read. fMRIPrep composite H5 files contain
#     multiple transform groups; group 2 holds the affine component of
#     the MNI-to-T1w warp, which is the component needed here.
#   - The exported affine matrices can be used to project MNI-space TMS
#     targets or atlas ROIs into each subject's native anatomical space
#     without requiring a full ANTs installation at the application stage.
# ==========================

for subj in subjects:
    for ses in sessions: 
        transform_file = glob.glob(os.path.join(FMRIPREP_PATH, f'sub-{subj}',f'ses-{ses}', 'anat', "*from-MNI152NLin2009cAsym_to-T1w_mode-image_xfm.h5"), recursive=True)[0]
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
        if not os.path.exists(os.path.join(TRANSFORM_PATH, f'sub-{subj}',f'ses-{ses}')):
            print(f"Folder '{os.path.join(TRANSFORM_PATH, f'sub-{subj}',f'ses-{ses}')}' does not exist. Creating it...")
            os.makedirs(os.path.join(TRANSFORM_PATH, f'sub-{subj}',f'ses-{ses}'))
        else:
            print(f"Folder '{os.path.join(TRANSFORM_PATH, f'sub-{subj}',f'ses-{ses}')}' already exists.") 
        np.savetxt(os.path.join(os.path.join(TRANSFORM_PATH, f'sub-{subj}',f'ses-{ses}'),
                                os.path.basename(transform_file).replace('_ses-pre','').replace('h5','txt')),transform.affine_matrix, delimiter=' ')