from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
from rsTMS_pipeline.preproc.preproc_utils import *
from rsTMS_pipeline.targeting.targeting_utils import *
from rsTMS_pipeline.plotting.plotting_utils import *
from nilearn.image import mean_img, load_img, clean_img,index_img

# ==========================
# Seed-based Functional Connectivity Analysis for MDD Subjects
#
# Author: Zaineb Amor
#
# This section performs the following steps for each subject and session (MDD protocol):
#
# 1. **Load fMRIPREP Data**
#    - Functional (BOLD), brain masks, confound files, anatomical images, and GM masks are loaded using `load_fmriprepdata`.
#    - Functional and mask files are sorted by run.
#
# 2. **Clean Functional Data**
#    - For each run:
#        * `clean_bold` removes confounds and performs preprocessing such as detrending and standardization.
#        * The mean functional image is computed for visualization.
#        * Optional: save mean cleaned BOLD images (currently commented out).
#
# 3. **Time Series Subsetting**
#    - Functional data is truncated to different lengths (`time_series_lengths`) to assess stability of connectivity.
#    - `index_img` is used to select the first N volumes.
#
# 4. **Seed-based Connectivity (SGC)**
#    - Define a seed in SGC (coordinates: 6,16,-10) and create spherical masks.
#    - Compute correlation maps between the seed and the rest of the brain using `sgc_coorelation_map`.
#    - ROI-based extraction over the DLPFC using `dlpfc_masking`.
#    - Identify the voxel with minimum z-value in the ROI (`min_target_roi`) and optionally visualize connectivity.
#
# 5. **Seed-based Connectivity over GM**
#    - Further restrict connectivity analysis to grey matter (`min_target_gm`) to refine target selection.
#    - Optional visualization of projected connectivity on surface (currently commented out).
#
# 6. **Memory Management**
#    - Delete intermediate variables after each step to save memory.
#
# Notes:
#    - Output files are saved in a dedicated `figures/fmriprep` directory.
#    - Visualization steps (plotting, surface projections) are currently commented out for speed but can be enabled for inspection.
#    - This analysis is specific to **MDD subjects**.
# ==========================


print(FMRIPREP_PATH)
time_series_lengths = [300, 600, 900, 1200]
for subj in subjects: 
    for ses in sessions: 
        print('SUBJECT:', subj, '- SESSION:', ses)
        FUNC_PATH, MASK_PATH, confounds_file, ANAT_PATH, GM_PATH = load_fmriprepdata(FMRIPREP_PATH, subj, ses, space)
        bold_files = sort_by_run(FUNC_PATH)
        mask_files = sort_by_run(MASK_PATH)            
        for i in range(len(bold_files)):
            print('Run:', i+1)
            clean_func_orig, mean_func, sample_mask, confounds = clean_bold(FUNC_PATH[i], tr=1.09)

            output_file = '/home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/rsTMS_pipeline/figures/fmriprep/'+f'Tsubj-{subj}_ses-{ses}_run-{i+1}_mean_cleaned_bold.png'
            if i==0: 
                title = "mean cleaned bold - MNI space: + 20"
            if i==1: 
                title = "mean cleaned bold - MNI space: + 30"
            coords=(6,16,-10)
            #disp = plotting.plot_img(mean_func,cut_coords=coords,title=title,cmap="gray")
            #disp.add_contours(nib.load(MASK_PATH[i]))
            #disp.add_markers([coords], marker_color='red', marker_size=30)
            #disp.savefig(output_file)  # Save the figure
            #plotting.show()
            
            for n_vols in time_series_lengths:
                clean_func = index_img(clean_func_orig, slice(0, n_vols))
                nscans = clean_func.shape[-1]
                sgc_masker,sgc_mask,sgc_mask_noncl = sgc_masking(FUNC_PATH[i],clean_func,nscans,radius_mm=10,seeds_sgc = [(6,16,-10)],tr=1.09)
                print('N_vols', n_vols, 'Nscans:', nscans, 'SGC mask shape:', sgc_mask.shape)
                correlation_img, correlation_map = sgc_coorelation_map(MASK_PATH[i], clean_func, sgc_mask,)
                
                roi_data, roi_img=dlpfc_masking(clean_func,MASK_PATH[i],seeds_dlpfc = [(-36,39,43), (-44,40,29), (-41,16,54)])
                output_file = '/home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/rsTMS_pipeline/figures/fmriprep/'+f'subj-{subj}_ses-{ses}_run-{i+1}_nvols-{n_vols}_roi.png'
                #disp_roi(roi_img, mean_func,output_file,title="DLPFC ROI (summed seeds)",coords=(-44,40,29)) 

                print('Over the DLPFC ROI')
                masked_correlation_img, min_voxel_idx, min_z_value, min_mni_coord = min_target_roi(correlation_img, roi_img)
                output_file = '/home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/rsTMS_pipeline/figures/fmriprep/'+f'subj-{subj}_ses-{ses}_run-{i+1}_nvols-{n_vols}_seed_based_fc_bm.png'
                #disp_connectivity(masked_correlation_img, roi_img, output_file, title="Seed-based SGC functional connectivity over brain mask", coords=min_mni_coord)
                #project_on_surf(masked_correlation_img, hemi='left',threshold=0.0, title="Seed-based SGC functional connectivity over brain mask",
                #output_file = '/home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/rsTMS_pipeline/figures/fmriprep/'+f'Msubj-{subj}_ses-{ses}_run-{i+1}_nvols-{n_vols}_seed_based_fc_bm_LeftHemiProjection',
                #mni_coord = list(min_mni_coord))

                del(masked_correlation_img, min_voxel_idx, min_z_value, min_mni_coord)
                
                print('Over the DLPFC ROI  and GM')
                final_projected_img, min_voxel_idx, min_z_value, min_mni_coord = min_target_gm(correlation_img, roi_img,GM_PATH[0])
                output_file = '/home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/rsTMS_pipeline/figures/fmriprep/'+f'subj-{subj}_ses-{ses}_run-{i+1}_nvols-{n_vols}_seed_based_fc_gm.png'
                #disp_connectivity(final_projected_img, roi_img, output_file, title="Seed-based SGC functional connectivity over brain mask and GM", coords=min_mni_coord)
                #project_on_surf(final_projected_img, hemi='left',threshold=0.0, title="Seed-based SGC functional connectivity over brain mask and GM",
                #output_file = '/home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/rsTMS_pipeline/figures/fmriprep/'+f'Msubj-{subj}_ses-{ses}_run-{i+1}_nvols-{n_vols}_seed_based_fc_gm_LeftHemiProjection',
                #mni_coord = list(min_mni_coord))

                del(final_projected_img, min_voxel_idx, min_z_value, min_mni_coord)
                del(clean_func, nscans,)
