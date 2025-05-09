#!/bin/bash

WORKDIR="/home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/Data"
subjects=("sub-P3")
for sub in "${subjects[@]}"
do
	for ses in 1
	do 
		SUBID="${sub}"
		SESID="ses-${ses%}"
		WORKSUBDIR="${WORKDIR%}/${SUBID%}/${SESID%}"
		mkdir $WORKSUBDIR
	singularity run --cleanenv \
		--bind /home/team/freesurfer/7.4.1/license.txt:/freesurfer-license.txt:ro \
		--bind /home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/Data/rawdata:/rawdata:ro \
		--bind /home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/Data/derivatives/fmriprep_sdc:/out:rw \
		--bind /home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/Data:/tmpdir:rw \
		/home/team/FMRIPREP/fmriprep-23.2.1.simg /rawdata /out  participant \
		--skip_bids_validation \
		--work-dir=/tmpdir --fs-license-file=/freesurfer-license.txt \
                --output-spaces func anat MNI152NLin2009cAsym fsnative \
		--dummy-scans 0 \
	#	--force-sdc \
        #        --me-t2s-fit-method curvefit \
	#	 --use-syn-sdc warn \
		
	rm -rf "$tmpdir"
	done
done
