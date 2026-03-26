#!/bin/bash

WORKDIR="/home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/anonym_data"

for sub in OUVfre
do
    for ses in 1
    do
        SUBID="sub-${sub}"
        SESID="ses-${ses}"
        WORKSUBDIR="${WORKDIR}/${SUBID}/${SESID}"

        #mkdir -p "$WORKSUBDIR"

        singularity run --cleanenv \
            --bind /home/team/freesurfer/7.4.1/license.txt:/freesurfer-license.txt:ro \
            --bind /home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/anonym_data/rawdata:/rawdata:ro \
            --bind /home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/anonym_data/derivatives/fmriprep:/out:rw \
            --bind /home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/tmp:/tmpdir:rw \
            /home/team/FMRIPREP/fmriprep-23.2.1.simg /rawdata /out participant \
            --skip_bids_validation \
            --work-dir /tmpdir \
            --fs-license-file /freesurfer-license.txt \
            --output-spaces func anat MNI152NLin2009cAsym fsnative \
            --dummy-scans 0

        rm -rf /home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/tmp/*

    done
done
