#CHARM directory to run in ==> Ouput
charm_dir="/home/zamor/Documents/dataset/MDD/derivatives/charmtms"
# Parent directory to search
parent_dir="/home/zamor/Documents/dataset/MDD/derivatives/fmriprep"
# Freesurfer directory
fs_dir="$parent_dir/sourcedata/freesurfer"
# Regular expression pattern for directories
dir_pattern="sub-*/ses-*"
# Regular expression pattern for files
file_pattern="*desc-preproc_T1w.nii.gz"
# Directory where I stored the affine transformations
transform_dir="/home/zamor/Documents/dataset/MDD/derivatives/h5_transforms/"
# Regular expression pattern for ANTs MNI to T1w transform
transform_pattern="_from-MNI152NLin2009cAsym_to-T1w_mode-image_xfm.txt"
# File to store names of directories where the file was not found
not_found_log="not_found.log"

if [ ! -d "$charm_dir" ]; then
    echo "Directory $charm_dir does not exist. Creating it..."
    sudo mkdir -p "$charm_dir"  # Create the directory if it doesn't exist
else
    echo "Directory $charm_dir already exists."
fi
cd $charm_dir

# Iterate over directories that match the pattern
#for dir in $(find "$parent_dir" -maxdepth 1 -type d -name "$dir_pattern")
for dir in $(find "$parent_dir" -type d -path "$parent_dir/$dir_pattern") 
do
	echo "Looking for T1w file in $dir"
	#file=$(find "$dir" -type f -name "$file_pattern" | grep -v 'space')
	file=$(find "$dir" -type f -name "$file_pattern" | grep -v 'space')
        echo "The file found is $file"	
	# Check if the file exists
	if [ -n "$file" ]; then
		# Store the directory name (not full path) as a variable
		#dir_name=$(basename "$dir")
		dir_name=$(basename "$(dirname "$dir")")_$(basename "$dir") 
		echo "T1w file found: checking if head modelling was fully performed for $dir_name"
		# model_log=$(find  "$charm_dir/m2m_$dir_name" -maxdepth 1 -type f -name "charm_report.html")
		# if [ -z "$model_log" ]; then
		model_msh=$(find  "$charm_dir/m2m_$dir_name" -maxdepth 1 -type f -name "$dir_name.msh")
		if [ -z "$model_msh" ]; then
		#model_surf=$(find "$charm_dir/m2m_$dir_name/surfaces" -maxdepth 1 -type f -name "lh.central.gii")
		#if [ -z "$model_surf" ]; then
			file_name=$(basename "$file")
			echo "Head model absent or incomplete: looking for matching freesurfer folder: $file_name"
                	# Look for pre-existing freesurfer output
			#FS_DIR=$(find "$fs_dir" -maxdepth 1 -type d -name "$dir_name")
			FS_DIR=$(find "$fs_dir" -maxdepth 1 -type d -name "$(basename "$(dirname "$dir")")")
			echo "fsdir $FS_DIR"

			if [ -d "$FS_DIR" ]; then
				echo "Freesurfer folder found: $FS_DIR, looking for ANTs MNI to T1w transform in $dir"
				#TRANSFORM=$(find "$dir" -type f -name "$transform_pattern")
				txt_transform_dir="${transform_dir}$(basename "$(dirname "$dir")")/$(basename "$dir")"
				TRANSFORM=$(find "$txt_transform_dir" -type f -name "*.txt")
			        echo "transform $TRANSFORM $h5_transform_dir"	
				if [ -n "$TRANSFORM" ]; then
					echo "ANTs MNI to T1w transform found: $TRANSFORM"
					echo "Running charm_tms on file $file_name"
					#charm_tms "$dir_name" --mesh
					charm_tms "$dir_name" "$file" --inittransform $TRANSFORM --fs-dir $FS_DIR --forcerun
					#--forceqform 
					echo " "
				else
					echo "ANTs MNI to T1w transform not found, moving onto next subject"
					echo " "
					#continue
				fi

			else
				echo "Freesurfer folder not found, moving onto next subject"
				echo " "
			fi
		else
			echo "Head model of $dir_name already exists, moving onto next subject"
			echo " "
		fi
	else
		echo "File not found in directory: $dir , moving onto next subject"
	    	# Store the name of the directory where the file was not found
	    	echo "$dir" >> "$not_found_log"
		echo " "
	fi
done
