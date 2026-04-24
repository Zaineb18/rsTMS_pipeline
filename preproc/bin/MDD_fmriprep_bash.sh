#!/bin/bash
RAWDATA="/home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/anonym_data/rawdata"
DERIVATIVES="/home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/anonym_data/derivatives/fmriprep"
TMPDIR="/home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/tmp"

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




#!/bin/bash

#WORKDIR="/home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/anonym_data"

#for sub in BERoum
#do
#    for ses in 1
#    do
#        SUBID="sub-${sub}"
#        SESID="ses-${ses}"
#        WORKSUBDIR="${WORKDIR}/${SUBID}/${SESID}"

        #mkdir -p "$WORKSUBDIR"

#        singularity run --cleanenv \
#            --bind /home/team/freesurfer/7.4.1/license.txt:/freesurfer-license.txt:ro \
#            --bind /home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/anonym_data/rawdata:/rawdata:ro \
#            --bind /home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/anonym_data/derivatives/fmriprep:/out:rw \
#            --bind /home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/tmp:/tmpdir:rw \
#            /home/team/FMRIPREP/fmriprep-23.2.1.simg /rawdata /out participant \
#            --skip_bids_validation \
#            --work-dir /tmpdir \
#            --fs-license-file /freesurfer-license.txt \
#            --output-spaces func anat MNI152NLin2009cAsym fsnative \
#            --dummy-scans 0 \
#            --skip-existing

#        rm -rf /home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/tmp/*

#    done
#done
