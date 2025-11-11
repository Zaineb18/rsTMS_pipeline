from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
from rsTMS_pipeline.preproc.preproc_utils import *

import glob
import os
import shutil

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