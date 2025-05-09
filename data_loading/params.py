import os
import glob 
import numpy as np

DATA_DIR = "/home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/Data"
space = "MNI152NLin2009cAsym"
subjects = ["P3"]
sessions = [1]
RAW_PATH = os.path.join(DATA_DIR, 'rawdata')
FMRIPREP_PATH =os.path.join(DATA_DIR, 'derivatives', 'fmriprep')
TRANSFORM_PATH = os.path.join(DATA_DIR, 'derivatives', 'h5_transforms')
CHARM_PATH =os.path.join(DATA_DIR, 'derivatives', 'charmtms')
SIMNIBS_PATH =os.path.join(DATA_DIR, 'derivatives', 'simnibs')
change_from_LPS_to_RAS = np.array([[1, -1, 1, 1], [-1, 1, 1, 1], [1, 1, 1, -1], [1, 1, 1, 1]])