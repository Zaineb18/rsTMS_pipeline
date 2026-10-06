#!/bin/bash

RAWDATA="/home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_HalluStim_2026/rawdata"
DERIVATIVES="/home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_HalluStim_2026/derivatives/fmriprep"
TMPDIR="/home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_HalluStim_2026/tmp"

# Build list of subjects without derivatives
SUBJECTS_TO_RUN=()
for sub_path in "${RAWDATA}"/sub-*/; do
    SUBID=$(basename "$sub_path")   # e.g. sub-OUVfre
    sub="${SUBID#sub-}"             # e.g. OUVfre

    if [ -d "${DERIVATIVES}/${SUBID}" ] && [ "$(ls -A "${DERIVATIVES}/${SUBID}" 2>/dev/null)" ]; then
        echo "SKIP: ${SUBID} — derivatives already exist"
    else
        echo "QUEUE: ${SUBID} — no derivatives found"
        SUBJECTS_TO_RUN+=("$sub")
    fi
done

if [ ${#SUBJECTS_TO_RUN[@]} -eq 0 ]; then
    echo "All subjects already preprocessed. Nothing to do."
    exit 0
fi

echo "Running fMRIPrep for: ${SUBJECTS_TO_RUN[*]}"
echo "Subjects to run array has ${#SUBJECTS_TO_RUN[@]} elements:"
printf '  [%s]\n' "${SUBJECTS_TO_RUN[@]}"

singularity run --cleanenv \
    --bind /home/team/freesurfer/7.4.1/license.txt:/freesurfer-license.txt:ro \
    --bind "${RAWDATA}":/rawdata:ro \
    --bind "${DERIVATIVES}":/out:rw \
    --bind "${TMPDIR}":/tmpdir:rw \
    /home/team/FMRIPREP/fmriprep-23.2.1.simg /rawdata /out participant \
    --skip_bids_validation \
    --work-dir /tmpdir \
    --fs-license-file /freesurfer-license.txt \
    --output-spaces func anat MNI152NLin2009cAsym fsnative \
    --me-t2s-fit-method curvefit \
    --ignore fieldmaps \
    --participant-label "${SUBJECTS_TO_RUN[@]}" 

rm -rf "${TMPDIR}"/*
