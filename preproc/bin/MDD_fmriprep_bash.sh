#!/bin/bash

WORKDIR="/home/zamor/Documents/dataset/MDD/"
for sub in 01
do
	for ses in 1
	do 
		#SUBID="${sub}"
		SUBID="sub-${sub%}"
		SESID="ses-${ses%}"
		WORKSUBDIR="${WORKDIR%}/${SUBID%}/${SESID%}"
		mkdir $WORKSUBDIR
	singularity run --cleanenv \
		--bind /home/team/freesurfer/7.4.1/license.txt:/freesurfer-license.txt:ro \
		--bind /home/zamor/Documents/dataset/MDD/rawdata:/rawdata:ro \
		--bind /home/zamor/Documents/dataset/MDD/derivatives/fmriprep:/out:rw \
		--bind /home/zamor/Documents/dataset/MDD/tmp:/tmpdir:rw \
		/home/team/FMRIPREP/fmriprep-23.2.1.simg /rawdata /out  participant \
		--skip_bids_validation \
		--work-dir=/tmpdir --fs-license-file=/freesurfer-license.txt \
                --output-spaces func anat MNI152NLin2009cAsym fsnative \
		--ignore fieldmaps		
#		--dummy-scans 0 \
	#	--use-syn-sdc \
	#	--force-sdc \
		
	rm -rf "$tmpdir"
	done
done
