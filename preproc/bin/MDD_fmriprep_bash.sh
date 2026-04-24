#!/bin/bash
RAWDATA="/home/team/rsTMS_dataset/anonym_data/rawdata"
DERIVATIVES="/home/team/rsTMS_dataset/anonym_data/derivatives/fmriprep"
TMPDIR="/home/team/rsTMS_dataset/tmp"

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
    --dummy-scans 0 \
    --participant-label "${SUBJECTS_TO_RUN[@]}" 

rm -rf "${TMPDIR}"/*
