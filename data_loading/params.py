import os
import glob 
import numpy as np

# ==========================
# Central configuration file. Set the proto variable to "MDD" or "SCZ"
# to switch between the two study protocols.

# Author: Zaineb Amor

# Edit this file before running any script to point to the correct data
# directory and select the subjects/sessions to process.
# ==========================

proto="MDD"

if proto=="SCZ":
    DATA_DIR = "/home/zamor/Documents/MainStim"
    space = "MNI152NLin2009cAsym"
    subjects = [8]
    sessions = [1]
    RAW_PATH = os.path.join(DATA_DIR, 'rawdata')
    SOURCE_PATH = os.path.join(DATA_DIR, 'sourcedata')    
    FMRIPREP_PATH =os.path.join(DATA_DIR, 'derivatives', 'fmriprep')
    TRANSFORM_PATH = os.path.join(DATA_DIR, 'derivatives', 'h5_transforms')
    CHARM_PATH =os.path.join(DATA_DIR, 'derivatives', 'charmtms')
    SIMNIBS_PATH =os.path.join(DATA_DIR, 'derivatives', 'simnibs')
    change_from_LPS_to_RAS = np.array([[1, -1, 1, 1], [-1, 1, 1, 1], [1, 1, 1, -1], [1, 1, 1, 1]])
elif proto=="MDD":
    DATA_DIR = "/home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/anonym_data"
    space = "MNI152NLin2009cAsym"
    subjects = ['OUVfre']
    sessions = [1]
    RAW_PATH = os.path.join(DATA_DIR, 'rawdata')
    SOURCE_PATH = os.path.join(DATA_DIR, 'sourcedata')
    FMRIPREP_PATH =os.path.join(DATA_DIR, 'derivatives', 'fmriprep')
    TRANSFORM_PATH = os.path.join(DATA_DIR, 'derivatives', 'h5_transforms')
    CHARM_PATH =os.path.join(DATA_DIR, 'derivatives', 'charmtms')
    SIMNIBS_PATH =os.path.join(DATA_DIR, 'derivatives', 'simnibs')
    FIGS_PATH = os.path.join(DATA_DIR, 'derivatives', 'figures')
    RES_PATH = os.path.join(DATA_DIR, 'derivatives', 'results')
    change_from_LPS_to_RAS = np.array([[1, -1, 1, 1], [-1, 1, 1, 1], [1, 1, 1, -1], [1, 1, 1, 1]])