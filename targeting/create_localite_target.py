from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
import os
from simnibs import opt_struct, mni2subject_coords
from simnibs import localite
import numpy as np
import pandas as pd


tms_opt = opt_struct.TMSoptimize()

for subject in subjects:
    for session in sessions: 
        results_file = os.path.join(RES_PATH, f'sub-{subject}', f'ses-{session}',
                     f'sub-{subject}_ses-{session}_targeting-results.csv')
        df = pd.read_csv(results_file, sep='\t')
        subset_df = df[(df["tissue"] == 'GM mask') & (df["stat"] == 'Fisher Z')]
        mni_coords = (int(subset_df['mni_x']), int(subset_df['mni_y']), int(subset_df['mni_z']))
        tms_opt.subpath = os.path.join(CHARM_PATH, f'm2m_sub-{subject}_ses-{session}')
        print(tms_opt.subpath)
        tms_opt.pathfem = os.path.join(SIMNIBS_PATH, f'sub-{subject}_ses-{session}_tmsoptim')
        os.makedirs(tms_opt.pathfem, exist_ok=True)
        print(tms_opt.pathfem)
        tms_opt.fnamecoil ='/home/zaineb/simnibs/resources/coil_models/Drakaki_BrainStim_2022/MagVenture_Cool-B65.ccd'
        tms_opt.target = mni2subject_coords(mni_coords, tms_opt.subpath)
        print('Target:', tms_opt.target, 'End Target')
        tms_opt.method = 'ADM'
        opt_pos=tms_opt.run()
        fn = os.path.join(tms_opt.pathfem, f'sub-{subject}_ses-{session}_opt_pos')
        localite().write(np.squeeze(opt_pos), fn)