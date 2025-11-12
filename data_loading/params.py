import os
import glob 
import numpy as np

proto="MDD"

if proto=="SCZ":
    DATA_DIR = "/home/zamor/Documents/MainStim"
    space = "MNI152NLin2009cAsym"
    subjects = [8]
    sessions = [1]
    RAW_PATH = os.path.join(DATA_DIR, 'rawdata')
    FMRIPREP_PATH =os.path.join(DATA_DIR, 'derivatives', 'fmriprep')
    TRANSFORM_PATH = os.path.join(DATA_DIR, 'derivatives', 'h5_transforms')
    CHARM_PATH =os.path.join(DATA_DIR, 'derivatives', 'charmtms')
    SIMNIBS_PATH =os.path.join(DATA_DIR, 'derivatives', 'simnibs')
    change_from_LPS_to_RAS = np.array([[1, -1, 1, 1], [-1, 1, 1, 1], [1, 1, 1, -1], [1, 1, 1, 1]])
elif proto=="MDD":
    DATA_DIR = "/Documents/rTMS_DomenechAmor_2025/Data_WORKSHOP"
    space = "MNI152NLin2009cAsym"
    subjects = [1]
    sessions = [1]
    RAW_PATH = os.path.join(DATA_DIR, 'rawdata')
    FMRIPREP_PATH =os.path.join(DATA_DIR, 'derivatives', 'fmriprep')
    TRANSFORM_PATH = os.path.join(DATA_DIR, 'derivatives', 'h5_transforms')
    CHARM_PATH =os.path.join(DATA_DIR, 'derivatives', 'charmtms')
    SIMNIBS_PATH =os.path.join(DATA_DIR, 'derivatives', 'simnibs')
    change_from_LPS_to_RAS = np.array([[1, -1, 1, 1], [-1, 1, 1, 1], [1, 1, 1, -1], [1, 1, 1, 1]])