from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
from rsTMS_pipeline.preproc.preproc_utils import *
from rsTMS_pipeline.targeting.targeting_utils import *
from rsTMS_pipeline.plotting.plotting_utils import *
from nilearn.image import mean_img, load_img, clean_img,index_img

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
            disp = plotting.plot_img(mean_func,cut_coords=coords,title=title,cmap="gray")
            disp.add_contours(nib.load(MASK_PATH[i]))
            disp.add_markers([coords], marker_color='red', marker_size=30)
            disp.savefig(output_file)  # Save the figure
            plotting.show()
            
            for n_vols in time_series_lengths:
                clean_func = index_img(clean_func_orig, slice(0, n_vols))
                nscans = clean_func.shape[-1]
                sgc_masker,sgc_mask,sgc_mask_noncl = sgc_masking(FUNC_PATH[i],clean_func,nscans,radius_mm=10,seeds_sgc = [(6,16,-10)],tr=1.09)
                print('N_vols', n_vols, 'Nscans:', nscans, 'SGC mask shape:', sgc_mask.shape)
                correlation_img, correlation_map = sgc_coorelation_map(MASK_PATH[i], clean_func, sgc_mask,)
                
                roi_data, roi_img=dlpfc_masking(clean_func,MASK_PATH[i],seeds_dlpfc = [(-36,39,43), (-44,40,29), (-41,16,54)])
                output_file = '/home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/rsTMS_pipeline/figures/fmriprep/'+f'subj-{subj}_ses-{ses}_run-{i+1}_nvols-{n_vols}_roi.png'
                disp_roi(roi_img, mean_func,output_file,title="DLPFC ROI (summed seeds)",coords=(-44,40,29)) 

                print('Over the DLPFC ROI')
                masked_correlation_img, min_voxel_idx, min_z_value, min_mni_coord = min_target_roi(correlation_img, roi_img)
                output_file = '/home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/rsTMS_pipeline/figures/fmriprep/'+f'subj-{subj}_ses-{ses}_run-{i+1}_nvols-{n_vols}_seed_based_fc_bm.png'
                disp_connectivity(masked_correlation_img, roi_img, output_file, title="Seed-based SGC functional connectivity over brain mask", coords=min_mni_coord)
                project_on_surf(masked_correlation_img, hemi='left',threshold=0.0, title="Seed-based SGC functional connectivity over brain mask",
                output_file = '/home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/rsTMS_pipeline/figures/fmriprep/'+f'Msubj-{subj}_ses-{ses}_run-{i+1}_nvols-{n_vols}_seed_based_fc_bm_LeftHemiProjection',
                mni_coord = list(min_mni_coord))

                del(masked_correlation_img, min_voxel_idx, min_z_value, min_mni_coord)
                
                print('Over the DLPFC ROI  and GM')
                final_projected_img, min_voxel_idx, min_z_value, min_mni_coord = min_target_gm(correlation_img, roi_img,GM_PATH[0])
                output_file = '/home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/rsTMS_pipeline/figures/fmriprep/'+f'subj-{subj}_ses-{ses}_run-{i+1}_nvols-{n_vols}_seed_based_fc_gm.png'
                disp_connectivity(final_projected_img, roi_img, output_file, title="Seed-based SGC functional connectivity over brain mask and GM", coords=min_mni_coord)
                project_on_surf(final_projected_img, hemi='left',threshold=0.0, title="Seed-based SGC functional connectivity over brain mask and GM",
                output_file = '/home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/rsTMS_pipeline/figures/fmriprep/'+f'Msubj-{subj}_ses-{ses}_run-{i+1}_nvols-{n_vols}_seed_based_fc_gm_LeftHemiProjection',
                mni_coord = list(min_mni_coord))

                del(final_projected_img, min_voxel_idx, min_z_value, min_mni_coord)
                del(clean_func, nscans,)
