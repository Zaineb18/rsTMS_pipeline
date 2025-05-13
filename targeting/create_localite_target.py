from rsTMS_pipeline.data_loading.params import *
import os
from simnibs import opt_struct, mni2subject_coords
from simnibs import localite
import numpy as np


subjects = ["MAINSTIM002FL"]
mni_coords = (-64,-38,34) 
# Initialize structure
tms_opt = opt_struct.TMSoptimize()

# Subject folder
for subject in subjects:
    for session in sessions: 
        tms_opt.subpath = os.path.join(CHARM_PATH, f'm2m_sub-{subject}_ses-{session}')
        print(tms_opt.subpath)
        #rf'D:\HALLUSTIM_BIDS\derivatives\charm_tms\m2m_sub-HALLUSTIM003MM'
        # Select output folder
        tms_opt.pathfem = os.path.join(SIMNIBS_PATH, f'sub-{subject}_ses-{session}_tmsoptimffinal')
        print(tms_opt.pathfem)
        #rf'D:\HALLUSTIM_BIDS\derivatives\simnibs\tms_optimization_adm_HALLUSTIM003MM'
        # Select the coil model
        # The ADM method requires a '.ccd' coil model
        tms_opt.fnamecoil ='/home/zaineb/simnibs/resources/coil_models/Drakaki_BrainStim_2022/MagVenture_Cool-B65.ccd'
        # Select a target for the optimization
        tms_opt.target = mni2subject_coords(mni_coords, tms_opt.subpath)
        print('Target:', tms_opt.target, 'End Target')
        # Use the ADM method
        tms_opt.method = 'ADM'
        # Run optimization
        opt_pos=tms_opt.run()
        fn = os.path.join(tms_opt.pathfem, f'sub-{subject}_ses-{session}_opt_pos')
        localite().write(np.squeeze(opt_pos), fn)