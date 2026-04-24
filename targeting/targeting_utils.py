import re
import os
from nilearn.image import mean_img, load_img, index_img, clean_img,math_img,new_img_like,resample_to_img
from nilearn.interfaces.fmriprep import load_confounds
from nilearn.maskers import NiftiSpheresMasker,NiftiMasker
import numpy as np
import nibabel as nib
from scipy.signal import detrend
from scipy.stats import pearsonr
from nibabel.affines import apply_affine

def sgc_masking(clean_func,radius_mm=10, seeds_sgc = [(6,16,-10)]): 
    sgc_masker = NiftiSpheresMasker(seeds_sgc,radius=radius_mm,t_r=1,allow_overlap=True)
    sgc_mask = sgc_masker.fit_transform(clean_func)
    sgc_mask_noncl= sgc_masker.fit_transform(clean_func)
    return(sgc_masker,sgc_mask,sgc_mask_noncl)

def quality_signal(fpath, mpath):
    bold_img = nib.load(fpath)  
    bold_data = bold_img.get_fdata()
    brain_mask_img = nib.load(mpath)
    brain_mask_data = brain_mask_img.get_fdata()
    masked_bold_data = bold_data * brain_mask_data[..., np.newaxis]
    detrended_bold_data = detrend(masked_bold_data, axis=-1)
    mean_signal = np.nanmean(masked_bold_data, axis=3)
    std_signal = np.nanstd(detrended_bold_data, axis=3)
    tsnr = mean_signal / std_signal
    tsnr_img = nib.Nifti1Image(tsnr, bold_img.affine) 
    mean_img = nib.Nifti1Image(mean_signal, bold_img.affine)
    std_img = nib.Nifti1Image(std_signal, bold_img.affine)
    (tsnr_img, mean_img, std_img)

def sgc_coorelation_map(mpath, clean_func, sgc_mask,):
    brain_masker = NiftiMasker(mask_img=mpath, standardize=True)
    brain_voxels = brain_masker.fit_transform(clean_func)
    print('NBrain voxels', brain_voxels.shape) 
    sgc_mask_standardized = (sgc_mask - np.mean(sgc_mask)) / np.std(sgc_mask)
    correlation_map = np.array([pearsonr(sgc_mask_standardized.ravel(), voxel_ts)[0] for voxel_ts in brain_voxels.T])
    correlation_img = brain_masker.inverse_transform(correlation_map)
    # ADD: Fisher r-to-z transform (makes variable name z_img actually correct)
    z_map = np.arctanh(np.clip(correlation_map, -0.9999, 0.9999))
    z_img = brain_masker.inverse_transform(z_map)        
    return(correlation_img, correlation_map, z_img, z_map) 

def _dlpfc_masking(clean_func,mpath,seeds_dlpfc = [(-36,39,43), (-44,40,29), (-41,16,54)]): 
    roi_data = np.zeros(clean_func.shape[:3]) 
    for seed in seeds_dlpfc:
        seed_masker = NiftiSpheresMasker([seed], radius=15, allow_overlap=True, mask_img=mpath)
        seed_data = seed_masker.fit_transform(clean_func) 
        seed_img = seed_masker.inverse_transform(seed_data[0])
        roi_data += seed_img.get_fdata()
    roi_data = (roi_data > 0).astype(np.uint8)
    roi_img = nib.Nifti1Image(roi_data, affine=clean_func.affine)   
    return(roi_data, roi_img)

def dlpfc_masking(clean_func, mpath, seeds_dlpfc=[(-36,39,43), (-44,40,29), (-41,16,54)]):
    roi_data = np.zeros(clean_func.shape[:3])
    ref_img = index_img(clean_func, 0)  # single volume as reference geometry
    
    for seed in seeds_dlpfc:
        seed_masker = NiftiSpheresMasker([seed], radius=15, allow_overlap=True, mask_img=mpath)
        seed_masker.fit(ref_img)
        # Get binary sphere directly from masker
        sphere_mask = seed_masker.inverse_transform(np.array([[1.0]]))
        roi_data += sphere_mask.get_fdata().squeeze()
    
    roi_data = (roi_data > 0).astype(np.uint8)
    roi_img = nib.Nifti1Image(roi_data, affine=clean_func.affine)
    return roi_data, roi_img

def min_target_roi(z_img, roi_img, fallback_coord=(-46, 46, 36)): 
    masked_z_img = math_img("z_img * (roi_img > 0)", z_img=z_img, roi_img=roi_img)
    dlpfc_roi_resampled = resample_to_img(roi_img, masked_z_img, interpolation='nearest')
    dlpfc_mask_data = dlpfc_roi_resampled.get_fdata() > 0
    masked_z_data = masked_z_img.get_fdata()
    masked_z_data[~dlpfc_mask_data] = np.nan  # Ignore values outside the ROI

    min_val = np.nanmin(masked_z_data)
    if min_val >= 0:
        print(f"WARNING: no anticorrelated voxel in DLPFC ROI "
              f"(min z = {min_val:.3f}). Using Fox fallback coord {fallback_coord}.")
        return masked_z_img, None, min_val, np.array(fallback_coord)
    min_voxel_idx = np.unravel_index(np.nanargmin(masked_z_data), masked_z_data.shape)
    min_mni_coord = apply_affine(masked_z_img.affine, min_voxel_idx)
    print(f"Max voxel index (in image space): {min_voxel_idx}")
    print(f"Max Z-score value: {masked_z_data[min_voxel_idx]}")
    print(f"Max Z-score MNI coordinates: {min_mni_coord}")
    return(masked_z_img, min_voxel_idx, masked_z_data[min_voxel_idx], min_mni_coord )

def gm_mask(gmpath, masked_z_img): 
    GM_probseg_resampled = resample_to_img(gmpath, masked_z_img, interpolation="nearest")
    GM_thresh = math_img("GM_probseg > 0.5", GM_probseg=GM_probseg_resampled)
    GM_thresh = new_img_like(GM_thresh, GM_thresh.get_fdata().squeeze())
    return(GM_thresh)

def _min_target_gm(z_img, roi_img,gmpath, fallback_coord=(-46, 46, 36)): 
    masked_z_img = math_img("z_img * (roi_img > 0)", z_img=z_img, roi_img=roi_img)
    GM_thresh = gm_mask(gmpath, masked_z_img)
    final_projected_img = math_img("masked_z_img * GM_thresh", masked_z_img=masked_z_img, GM_thresh=GM_thresh)
    gm_data = GM_thresh.get_fdata().squeeze() > 0
    final_projected_data[~gm_data] = np.nan
    final_projected_data[~dlpfc_mask_data] = np.nan    
    dlpfc_roi_resampled = resample_to_img(roi_img, final_projected_img, interpolation='nearest')
    dlpfc_mask_data = dlpfc_roi_resampled.get_fdata() > 0 
    final_projected_data = final_projected_img.get_fdata()
    final_projected_data[~dlpfc_mask_data] = np.nan  

    min_val = np.nanmin(final_projected_data)
    if min_val >= 0:
        print(f"WARNING: no anticorrelated GM voxel in DLPFC ROI "
              f"(min z = {min_val:.3f}). Using Fox fallback coord {fallback_coord}.")
        return final_projected_img, None, min_val, np.array(fallback_coord)
    min_voxel_idx = np.unravel_index(np.nanargmin(final_projected_data), final_projected_data.shape)
    min_mni_coord = apply_affine(final_projected_img.affine, min_voxel_idx)
    print(f"Max voxel index (in image space): {min_voxel_idx}")
    print(f"Max Z-score value: {final_projected_data[min_voxel_idx]}")
    print(f"Max Z-score MNI coordinates: {min_mni_coord}")
    return(final_projected_img, min_voxel_idx, final_projected_data[min_voxel_idx] ,min_mni_coord)

def min_target_gm(z_img, roi_img, gmpath, fallback_coord=(-46, 46, 36)):
    masked_z_img = math_img("z_img * (roi_img > 0)", z_img=z_img, roi_img=roi_img)
    GM_thresh = gm_mask(gmpath, masked_z_img)
    final_projected_img = math_img("masked_z_img * GM_thresh", masked_z_img=masked_z_img, GM_thresh=GM_thresh)

    dlpfc_roi_resampled = resample_to_img(roi_img, final_projected_img, interpolation='nearest')
    dlpfc_mask_data = dlpfc_roi_resampled.get_fdata() > 0
    gm_data = GM_thresh.get_fdata().squeeze() > 0

    final_projected_data = final_projected_img.get_fdata()   # ← assign FIRST
    final_projected_data[~gm_data] = np.nan                  # ← then mask
    final_projected_data[~dlpfc_mask_data] = np.nan

    min_val = np.nanmin(final_projected_data)
    if min_val >= 0:
        print(f"WARNING: no anticorrelated GM voxel in DLPFC ROI "
              f"(min z = {min_val:.3f}). Using Fox fallback coord {fallback_coord}.")
        return final_projected_img, None, min_val, np.array(fallback_coord)

    min_voxel_idx = np.unravel_index(np.nanargmin(final_projected_data), final_projected_data.shape)
    min_mni_coord = apply_affine(final_projected_img.affine, min_voxel_idx)  # ← fixed affine
    print(f"Min voxel index (in image space): {min_voxel_idx}")
    print(f"Min Z-score value: {final_projected_data[min_voxel_idx]}")
    print(f"Min Z-score MNI coordinates: {min_mni_coord}")
    return final_projected_img, min_voxel_idx, final_projected_data[min_voxel_idx], min_mni_coord