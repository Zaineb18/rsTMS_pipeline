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
│   ├── sgc_dlpfc_connectivity.py
│   └── targeting_utils.py
├── plotting/               # Visualisation utilities
│   └── plotting_utils.py
├── notebooks/              # Exploratory and demonstration notebooks
│   ├── example_MDD.ipynb
│   ├── example_SCZ.ipynb
│   └── target_stability.ipynb
└── __init__.py
```
---

## Full pipeline order
```
1. convert_to_bids.sh           ← convert DICOMs to BIDS NIfTI
2. remove_dummy_scans.py        ← remove non-steady-state volumes
3. ap_pa.py                     ← generate AP fieldmaps, set IntendedFor
4. MDD_fmriprep_bash.sh         ← run fMRIPrep (MDD protocol)
   or SZC_fmriprep_bash.sh      ← run fMRIPrep (SCZ protocol)
5. denoise.py                   ← confound regression on fMRIPrep output
6. sgc_dlpfc_connectivity.py    ← SGC–DLPFC connectivity and TMS targeting [MDD only]
   (SCZ targeting: BrainVoyager) ← separate pipeline, not included here
7. h5py2txt.py                  ← export MNI→T1w affine transforms, can also be run in parallel to the targeting
8. charmtms_bash.sh             ← run SimNIBS CHARM head modelling, can also be run in parallel to the targeting
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

Applies confound regression to fMRIPrep-preprocessed BOLD data using `clean_bold()` from `preproc_utils.py`.

For each subject and session, `load_fmriprepdata()` retrieves the BOLD, brain mask, confounds TSV, T1w, and grey matter paths. The script then detects whether run labels are present in the filenames and, if so, sorts all file lists by run number to ensure correct pairing across runs. Single-run sessions are handled transparently.

For each (BOLD, mask, confounds) triplet, `clean_bold()` is called, which:

1. Loads confound regressors from the fMRIPrep TSV via nilearn's `load_confounds`, using motion parameters (6 params + temporal derivatives) and WM/CSF mean signals as the denoising strategy. The confounds TSV path is resolved automatically from the BOLD file path — it does not need to be passed separately.
2. Cleans the BOLD image by regressing out confounds, and restricting processing to in-brain voxels via the brain mask.

The denoised image is saved alongside the fMRIPrep output with `preproc_bold_cleaned` replacing `preproc_bold` in the filename.

**Dependencies:** `nilearn`

---

### `h5py2txt.py`

Exports the MNI-to-T1w affine transformation matrix from fMRIPrep's `.h5` output into a plain `.txt` file for use in SimNIBS CHARM head modelling.

For each subject and session, the script locates the fMRIPrep-generated H5 file encoding the inverse transform (`from-MNI152NLin2009cAsym_to-T1w_mode-image_xfm.h5`) using a glob on the subject's `anat/` directory.

The H5 file is opened with `h5py` and `TransformGroup/2` is read — the group containing the affine component of the MNI-to-T1w warp. Two arrays are extracted:

- `TransformParameters`: a flat array of 12 values encoding the 3×3 rotation/scaling matrix (indices 0–8) and the 3D translation vector (indices 9–11).
- `TransformFixedParameters`: the 3D centre of rotation, stored separately following ITK's `MatrixOffsetTransformBase` convention.

A `MatrixOffsetTransformBase` object is instantiated with the matrix, translation, and centre. `compute_offset()` derives the effective translation offset accounting for the centre of rotation (`offset = translation + center − matrix @ center`), and `generate_affine_matrix()` assembles the full 4×4 homogeneous affine matrix. All intermediate components are printed for verification.

The output directory (`TRANSFORM_PATH/sub-XX/ses-X/`) is created if it does not already exist. The affine matrix is saved as a space-delimited `.txt` file whose name is derived from the H5 filename by stripping the protocol-specific `_ses-pre` suffix and replacing the `.h5` extension with `.txt`.

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

## Targeting (`targeting/`)

### `targeting/sgc_dlpfc_connectivity.py` ⚠️ MDD protocol only

Computes individualized TMS targets from resting-state fMRI data by identifying
the DLPFC site most anticorrelated with the subgenual cingulate cortex (SGC),
following Fox et al. (Biol Psychiatry 2012).

> **Note:** This script is specific to the **MDD protocol**. The SCZ protocol
> uses a separate targeting pipeline implemented in BrainVoyager.

**What it does**, for each subject and session:

1. Loads fMRIPrep outputs via `load_fmriprepdata()` (BOLD, brain mask,
   confounds, T1w, GM segmentation).
2. Denoises the BOLD image via `clean_bold()` (motion + WM/CSF confound
   regression).
3. Computes a whole-brain SGC seed-based connectivity map (10 mm sphere,
   MNI: 6, 16, −10) using voxelwise Pearson correlation. Both a raw Pearson r
   map and a Fisher z-transformed map are returned.
4. Constructs a binary DLPFC ROI from three 15 mm spheres centred on Fox 2013
   target coordinates: (−36, 39, 43), (−44, 40, 29), (−41, 16, 54).
5. Identifies the voxel with the minimum (most anticorrelated) connectivity
   value within the DLPFC ROI, under two tissue masks:
     - **Brain mask** — whole-brain, first-pass estimate
     - **GM mask** — grey matter only (probability > 0.5), recommended
       final clinical target
6. Compares the individualized coordinate against the Fox group-level standard
   (−46, 46, 36) and reports the Euclidean distance.
7. Saves figures and a per-run TSV results file.

**Outputs** saved under `rsTMS_pipeline/figures/sub-XX/ses-XX/`:

| File | Content |
|---|---|
| `*_meanbold.png` | Mean BOLD with SGC seed marker and brain mask contour |
| `*_roidlpfc.png` | DLPFC ROI overlaid on mean BOLD |
| `*_{stat}map-{tissue}.png` | SGC connectivity map with ROI contour and target marker |
| `*_{stat}surf-{tissue}.png` | Left hemisphere surface projection |
| `*_target-comparison-vol_{stat}map-{tissue}.png` | 4-panel volume comparison: individual vs Fox standard |
| `*_target-comparison-surf_{stat}map-{tissue}.png` | Surface comparison: individual vs Fox standard |

**Results** saved under `rsTMS_pipeline/results/sub-XX/ses-XX/`:

| File | Content |
|---|---|
| `*_targeting-results.csv` | TSV with MNI coordinates, connectivity values, and distances for all (stat × tissue) combinations |

**Result columns:**

| Column | Description |
|---|---|
| `subject`, `session`, `run` | BIDS identifiers |
| `stat` | `Pearson Correlation` or `Fisher Z` |
| `tissue` | `brain mask` or `GM mask` |
| `mni_x/y/z` | Individualized target coordinate (mm, rounded) |
| `min_connectivity` | Connectivity value at target (r or z, should be negative) |
| `std_x/y/z` | Fox standard coordinate (−46, 46, 36) |
| `distance_mm` | Euclidean distance: individual vs standard |
| `delta_x/y/z_mm` | Per-axis displacement |
| `used_fallback` | `True` if no anticorrelated voxel found; Fox coord used |

**Dependencies:** `nilearn`, `scipy`, `nibabel`, `numpy`, `pandas`

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