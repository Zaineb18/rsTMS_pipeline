# rsTMS_pipeline

A Python pipeline for preprocessing and targeting resting-state fMRI data in the context of fMRI-guided TMS (Transcranial Magnetic Stimulation) studies. It supports two clinical protocols: MDD (Major Depressive Disorder) and SCZ (Schizophrenia).

---

## Repository Structure

```
rsTMS_pipeline/
├── data_loading/           # Parameters and utilities for loading BIDS data
│   ├── params.py           # Protocol-specific paths and subject/session lists
│   ├── loading_utils.py    # Functions to locate NIfTI files at each pipeline stage
│   └── bin/
│       └── convert_to_bids.sh  # DICOM → NIfTI + BIDS organisation
├── preproc/                # Preprocessing scripts
│   ├── remove_dummy_scans.py
│   ├── ap_pa.py
│   ├── denoise.py
│   ├── h5py2txt.py
│   ├── preproc_utils.py
│   └── bin/
│       ├── MDD_fmriprep_bash.sh
│       ├── SZC_fmriprep_bash.sh
│       └── charmtms_bash.sh
├── targeting/              # Functional connectivity and TMS target identification
├── plotting/               # Visualisation utilities
├── notebooks/              # Exploratory and demonstration notebooks
├── figures/                # Output figures
└── __init__.py
```

---

## Data Loading (`data_loading/`)

### `bin/convert_to_bids.sh`

Converts raw DICOM files to NIfTI and organises them into a BIDS-compliant `rawdata/` directory.

**Usage:**
```bash
bash data_loading/bin/convert_to_bids.sh /path/to/rTMS_data
```

**What it does:**
- Expects sourcedata organised as `sourcedata/sub-*/<hash>/<series>/Unknown Study/`
- Infers the BIDS folder and suffix for each series from the series name (case-insensitive matching on `t1`, `t2`, `invpe`, `bold`)
- Converts matching series using `dcm2niix` (`-z y` for gzip NIfTI output)
- Outputs to `rawdata/sub-*/ses-1/{anat,fmap,func}/`
- Skips series with no DICOM files or no recognised BIDS match, with informative warnings
- Does not abort on individual series failures (`set +e`) so the full dataset is processed even if some series fail

**Dependencies:** `dcm2niix`

---

### `params.py`

Central configuration file. Set the `proto` variable to `"MDD"` or `"SCZ"` to switch between the two study protocols. Each protocol defines:

- `DATA_DIR` — root directory for all data
- `subjects`, `sessions` — lists of subject IDs and session numbers to process
- `RAW_PATH` — BIDS rawdata directory
- `SOURCE_PATH` — DICOM sourcedata directory
- `FMRIPREP_PATH` — fMRIPrep derivatives directory
- `TRANSFORM_PATH` — output directory for exported affine transforms (`.txt`)
- `CHARM_PATH` — SimNIBS CHARM head model output directory
- `SIMNIBS_PATH` — SimNIBS simulation output directory
- `space` — MNI template space used throughout (`MNI152NLin2009cAsym`)

**Edit this file** before running any script to point to the correct data directory and select the subjects/sessions to process.

---

### `loading_utils.py`

Utility functions that return lists of NIfTI file paths at different stages of the pipeline, using `glob` to find files matching BIDS naming conventions.

| Function | Returns |
|---|---|
| `load_sourcedata(SOURCE_PATH, subj, ses)` | BOLD and fmap NIfTI paths from `sourcedata/` |
| `load_rawdata(RAW_PATH, subj, ses)` | BOLD and fmap NIfTI paths from `rawdata/` |
| `load_fmriprepdata(FMRIPREP_PATH, subj, ses, space)` | fMRIPrep outputs: BOLD, brain mask, confounds TSV, T1w, GM probability map |

---

## Preprocessing (`preproc/`)

### Full pipeline order

```
1. convert_to_bids.sh       ← convert DICOMs to BIDS NIfTI
2. remove_dummy_scans.py    ← remove non-steady-state volumes
3. ap_pa.py                 ← generate AP fieldmaps, set IntendedFor
4. MDD_fmriprep_bash.sh     ← run fMRIPrep (MDD protocol)
   or SZC_fmriprep_bash.sh  ← run fMRIPrep (SCZ protocol)
5. denoise.py               ← confound regression on fMRIPrep output
6. h5py2txt.py              ← export MNI→T1w affine transforms from fMRIPrep H5 files
7. charmtms_bash.sh         ← run SimNIBS CHARM head modelling
```
---

### `remove_dummy_scans.py`

Removes dummy scans (non-steady-state volumes) from BOLD and fieldmap NIfTI files before fMRIPrep.

- Drops the first 10 volumes from each BOLD file (scanner warm-up / T1 equilibration period).
- Extracts a single representative volume (index 11) from each fieldmap to produce a static EPI reference.
- Overwrites original files in place.
- Handles both single-run and multi-run sessions automatically (files are sorted by run number only when run labels are present in filenames).

---

### `ap_pa.py`

Generates AP (anterior-posterior) fieldmaps from BOLD data and sets the `IntendedFor` field in all fieldmap JSON sidecars, as required by fMRIPrep.

**Loop 1 — AP fieldmap generation:**
- Extracts volume index 1 from each trimmed BOLD image as a static AP-direction EPI reference.
- Saves it as a new NIfTI file with `dir-AP` in the filename (derived from the existing `dir-PA` fmap path).
- Copies the BOLD JSON sidecar and renames it to match the new AP fieldmap.

**Loop 2 — IntendedFor linking:**
- For each fieldmap JSON sidecar, identifies the corresponding BOLD run (matched by run number in multi-run sessions, or by default in single-run sessions).
- Writes the BIDS-compliant relative path (`ses-X/func/filename.nii.gz`) into the `IntendedFor` field so that fMRIPrep knows which BOLD run each fieldmap should correct.
- Uses `json5` when reading sidecars to tolerate minor formatting issues in scanner-exported JSON files.

---

### `bin/MDD_fmriprep_bash.sh` and `bin/SZC_fmriprep_bash.sh`

Bash scripts that run [fMRIPrep](https://fmriprep.org) via Singularity for each protocol.

Both scripts loop over subjects and sessions and call fMRIPrep 23.2.1 with the following shared options:
- Output spaces: `func`, `anat`, `MNI152NLin2009cAsym`, `fsnative`
- FreeSurfer license mounted read-only
- `--skip_bids_validation`
- Working directory cleaned up after each run

**Protocol differences:**

| | MDD | SCZ |
|---|---|---|
| Script | `MDD_fmriprep_bash.sh` | `SZC_fmriprep_bash.sh` |
| Fieldmap correction | Uses AP/PA fieldmaps (generated by `ap_pa.py`) | `--ignore fieldmaps` (fieldmaps not acquired) |
| Multi-echo | — | `--me-t2s-fit-method curvefit` (multi-echo acquisition) |

**Usage:**
```bash
bash preproc/bin/MDD_fmriprep_bash.sh
bash preproc/bin/SZC_fmriprep_bash.sh
```

Update the subject/session lists and directory paths at the top of each script before running.

**Dependencies:** Singularity, fMRIPrep 23.2.1 `.simg`, FreeSurfer license

---

### `denoise.py`

Applies confound regression to fMRIPrep-preprocessed BOLD data.

- For each subject and session, loads the fMRIPrep BOLD image, T1w anatomical, and brain mask.
- Loads confound regressors using nilearn's `load_confounds` with the `motion` and `wm_csf` strategy (motion parameter derivatives + white matter and CSF signals).
- Cleans the BOLD image using `nilearn.image.clean_img` with linear detrending and no standardisation.
- Saves the denoised image as a new file with `preproc_bold_cleaned` in the filename, alongside the original fMRIPrep output.

**Dependencies:** `nilearn`

---

### `h5py2txt.py`

Exports the MNI-to-T1w affine transformation matrix from fMRIPrep's `.h5` output into a plain `.txt` file for use in SimNIBS CHARM head modelling.

- Locates the `from-MNI152NLin2009cAsym_to-T1w_mode-image_xfm.h5` file produced by fMRIPrep for each subject/session.
- Opens it with `h5py` and reads `TransformParameters` (rotation matrix + translation) and `TransformFixedParameters` (centre of rotation) from `TransformGroup/2`.
- Reconstructs the full 4×4 affine matrix using a `MatrixOffsetTransformBase` helper (defined in `preproc_utils.py`).
- Saves the result as a `.txt` file in `derivatives/h5_transforms/sub-XX/ses-X/`, creating the output folder if needed.

This exported transform is used by `charmtms_bash.sh` to initialise head model registration.

**Dependencies:** `h5py`, `numpy`

---

### `bin/charmtms_bash.sh`

Runs [SimNIBS CHARM](https://simnibs.github.io/simnibs/) head modelling for each subject, using fMRIPrep outputs and the exported affine transforms.

- Iterates over all `sub-*/ses-*` directories in the fMRIPrep derivatives folder.
- For each subject, locates the native-space T1w image (`*desc-preproc_T1w.nii.gz`).
- Skips subjects whose head model (`.msh` file) already exists.
- For subjects needing modelling, looks for a pre-existing FreeSurfer output directory and the exported ANTs MNI-to-T1w `.txt` transform.
- If both are found, runs `charm_tms` with `--inittransform`, `--fs-dir`, and `--forcerun`.
- Logs any subjects for whom the T1w file was not found to `not_found.log`.

**Usage:**
```bash
bash preproc/bin/charmtms_bash.sh
```

Update the directory paths at the top of the script before running.

**Dependencies:** SimNIBS (`charm_tms` must be available in `PATH`)

---

## Requirements

- Python ≥ 3.9
- [nibabel](https://nipy.org/nibabel/)
- [nilearn](https://nilearn.github.io/)
- [h5py](https://www.h5py.org/)
- [json5](https://pypi.org/project/json5/)
- [numpy](https://numpy.org/)

Install Python dependencies:
```bash
pip install nibabel nilearn h5py json5 numpy
```

External tools (must be installed separately):
- [dcm2niix](https://github.com/rordenlab/dcm2niix) — DICOM conversion
- [fMRIPrep 23.2.1](https://fmriprep.org) via Singularity
- [SimNIBS](https://simnibs.github.io/simnibs/) — head modelling (`charm_tms`)
- FreeSurfer license file

---

## Data Format

Input data must follow the [BIDS specification](https://bids.neuroimaging.io/). Expected structure after DICOM conversion:

```
rawdata/
└── sub-<label>/
    └── ses-<label>/
        ├── anat/
        │   └── sub-<label>_ses-<label>_T1w.nii.gz
        ├── func/
        │   └── sub-<label>_ses-<label>_task-restingstate_bold.nii.gz
        │   └── sub-<label>_ses-<label>_task-restingstate_bold.json
        └── fmap/
            └── sub-<label>_ses-<label>_dir-PA_epi.nii.gz
            └── sub-<label>_ses-<label>_dir-PA_epi.json
```

Subjects, sessions, and all directory paths are configured in `data_loading/params.py`.

---

## License

MIT — see [LICENSE](LICENSE) for details.