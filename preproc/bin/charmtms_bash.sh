# CHARM directory to run in ==> Output
charm_dir="/home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/anonym_data/derivatives/charmtms"
# Parent directory to search
parent_dir="/home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/anonym_data/derivatives/fmriprep"
# Freesurfer directory
fs_dir="$parent_dir/sourcedata/freesurfer"
# Regular expression pattern for files
file_pattern="*desc-preproc_T1w.nii.gz"
# Directory where I stored the affine transformations
transform_dir="/home/zamor/Documents/rTMS_DomenechAmor_2025/DomenechAmor_MDDrsTMS_2026/anonym_data/derivatives/h5_transforms/"
# Regular expression pattern for ANTs MNI to T1w transform
transform_pattern="_from-MNI152NLin2009cAsym_to-T1w_mode-image_xfm.txt"
# File to store names of directories where the file was not found
not_found_log="not_found.log"

if [ ! -d "$charm_dir" ]; then
    echo "Directory $charm_dir does not exist. Creating it..."
    sudo mkdir -p "$charm_dir"
else
    echo "Directory $charm_dir already exists."
fi

cd "$charm_dir"

for dir in $(find "$parent_dir" -mindepth 2 -maxdepth 2 -type d -name "ses-*"); do

    echo "Looking for T1w file in $dir"
    file=$(find "$dir" -type f -name "$file_pattern" | grep -v 'space')
    echo "The file found is $file"

    if [ -n "$file" ]; then
        sub=$(basename "$(dirname "$dir")")
        ses=$(basename "$dir")
        dir_name="${sub}_${ses}"
        out_dir="$charm_dir/$sub/$ses"
        mkdir -p "$out_dir"

        echo "T1w file found: checking if head modelling was fully performed for $dir_name"
        model_msh=$(find "$out_dir/m2m_$dir_name" -maxdepth 1 -type f -name "$dir_name.msh" 2>/dev/null)

        if [ -z "$model_msh" ]; then
            file_name=$(basename "$file")
            echo "Head model absent or incomplete: looking for matching freesurfer folder: $file_name"
            FS_DIR=$(find "$fs_dir" -maxdepth 1 -type d -name "$sub")
            echo "fsdir $FS_DIR"

            if [ -d "$FS_DIR" ]; then
                echo "Freesurfer folder found: $FS_DIR, looking for ANTs MNI to T1w transform"
                txt_transform_dir="${transform_dir}${sub}/${ses}"
                TRANSFORM=$(find "$txt_transform_dir" -type f -name "*.txt")
                echo "transform $TRANSFORM"

                if [ -n "$TRANSFORM" ]; then
                    echo "ANTs MNI to T1w transform found: $TRANSFORM"
                    echo "Running charm_tms on file $file_name"
                    charm_tms "$dir_name" "$file" --inittransform "$TRANSFORM" --fs-dir "$FS_DIR" --forcerun
                    mv "$charm_dir/m2m_$dir_name" "$out_dir/"
                    echo " "
                else
                    echo "ANTs MNI to T1w transform not found, moving onto next subject"
                    echo " "
                fi
            else
                echo "Freesurfer folder not found, moving onto next subject"
                echo " "
            fi
        else
            echo "Head model of $dir_name already exists at $out_dir, skipping"
            echo " "
        fi
    else
        echo "File not found in directory: $dir, moving onto next subject"
        echo "$dir" >> "$not_found_log"
        echo " "
    fi
done

