from rsTMS_pipeline.data_loading.loading_utils import *
from rsTMS_pipeline.preproc.preproc_utils import *
from rsTMS_pipeline.targeting.targeting_utils import *
from rsTMS_pipeline.plotting.plotting_utils import *
from nilearn import plotting, image, masking
from nilearn.input_data import NiftiSpheresMasker
import os
import glob 
import numpy as np

DATA_DIR = "/home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/Data"
space = "MNI152NLin2009cAsym"
FMRIPREP_PATH =os.path.join(DATA_DIR, 'derivatives', 'fmriprep_sdc')
FUNC_PATH, MASK_PATH, confounds_file, ANAT_PATH, GM_PATH = load_fmriprepdata(FMRIPREP_PATH, 'P3', 1, space)
print(FUNC_PATH)

fmri_vols1 = image.load_img(FUNC_PATH[0])
fmri_vols1 = image.index_img(fmri_vols1, slice(0, 600))
fmri_mean1 = image.mean_img(fmri_vols1)
std_vols1 = image.math_img('np.std(img, axis=3)', img=fmri_vols1)
mean_data1 = masking.apply_mask(fmri_mean1, MASK_PATH[0])  # 1D array: voxel values
std_data1 = masking.apply_mask(std_vols1, MASK_PATH[0])
global_mean_signal = np.mean(mean_data1)  # Mean across brain
global_std_signal = np.mean(std_data1)    # Mean std across brain
print(f"20° \n Global Mean Signal (over brain): {global_mean_signal:.2f}")
print(f"Global Std Signal (over brain): {global_std_signal:.2f}")

fmri_vols2 = image.load_img(FUNC_PATH[1])
fmri_mean2 = image.mean_img(fmri_vols2)
std_vols2 = image.math_img('np.std(img, axis=3)', img=fmri_vols2)
mean_data2 = masking.apply_mask(fmri_mean2, MASK_PATH[1])  # 1D array: voxel values
std_data2 = masking.apply_mask(std_vols2, MASK_PATH[1])
global_mean_signal = np.mean(mean_data2)  # Mean across brain
global_std_signal = np.mean(std_data2)    # Mean std across brain
print(f"30° \n  Global Mean Signal (over brain): {global_mean_signal:.2f}")
print(f"Global Std Signal (over brain): {global_std_signal:.2f}")



brain_only_mean = image.math_img('img1 * img2', img1=fmri_mean2, img2=image.load_img( MASK_PATH[1]))
brain_only_std = image.math_img('img1 * img2', img1=std_vols2, img2=image.load_img( MASK_PATH[1]))
plotting.plot_stat_map(brain_only_mean, title="Masked Mean Signal - 30°", vmax=5e3,threshold=0, cut_coords=(6, 16, -10))
plotting.show()
plotting.plot_stat_map(brain_only_std, title="Masked STD Signal - 30°", vmax=7e2,threshold=0, cut_coords=(6, 16, -10))
plotting.show()


seed_coords = [(6, 16, -10)]  # MNI coordinate
radius = 10  # in mm
# Create a spheres masker
seed_masker = NiftiSpheresMasker(
    seed_coords,
    radius=radius,
    detrend=False,
    standardize=False,
    memory='nilearn_cache'
)

time_series = seed_masker.fit_transform(fmri_vols2)
mean_signal_per_time = np.mean(time_series, axis=1)  # mean over voxels for each time point
mean_signal = np.mean(mean_signal_per_time)          # mean across time
std_signal = np.std(mean_signal_per_time)             # std across time

print(f"Mean Signal in Seed: {mean_signal:.2f}")
print(f"Std Signal in Seed: {std_signal:.2f}")
print(f"tSNR in Seed: {mean_signal/std_signal:.2f}")


################################################################################################
DATA_DIR = "/home/zamor/Documents/rTMSDepressionPilotes_DomenechAmor_2025/Data"
space = "MNI152NLin2009cAsym"
FMRIPREP_PATH =os.path.join(DATA_DIR, 'derivatives', 'fmriprep')
FUNC_PATH, MASK_PATH, confounds_file, ANAT_PATH, GM_PATH = load_fmriprepdata(FMRIPREP_PATH, 'P3', 1, space)
print(FUNC_PATH)
fmri_vols1 = image.load_img(FUNC_PATH[0])
fmri_vols1 = image.index_img(fmri_vols1, slice(0, 600))
fmri_mean1 = image.mean_img(fmri_vols1)
std_vols1 = image.math_img('np.std(img, axis=3)', img=fmri_vols1)
mean_data1 = masking.apply_mask(fmri_mean1, MASK_PATH[0])  # 1D array: voxel values
std_data1 = masking.apply_mask(std_vols1, MASK_PATH[0])

fmri_vols2 = image.load_img(FUNC_PATH[1])
fmri_mean2 = image.mean_img(fmri_vols2)
std_vols2 = image.math_img('np.std(img, axis=3)', img=fmri_vols2)
mean_data2 = masking.apply_mask(fmri_mean2, MASK_PATH[1])  # 1D array: voxel values
std_data2 = masking.apply_mask(std_vols2, MASK_PATH[1])


FMRIPREP_PATH =os.path.join(DATA_DIR, 'derivatives', 'fmriprep_sdc')
FUNC_PATH, MASK_PATH, confounds_file, ANAT_PATH, GM_PATH = load_fmriprepdata(FMRIPREP_PATH, 'P3', 1, space)
print(FUNC_PATH)
fmri_vols3 = image.load_img(FUNC_PATH[0])
fmri_vols3 = image.index_img(fmri_vols3, slice(0, 600))
fmri_mean3 = image.mean_img(fmri_vols3)
std_vols3 = image.math_img('np.std(img, axis=3)', img=fmri_vols1)
mean_data3 = masking.apply_mask(fmri_mean3, MASK_PATH[0])  # 1D array: voxel values
std_data3 = masking.apply_mask(std_vols3, MASK_PATH[0])

fmri_vols4 = image.load_img(FUNC_PATH[1])
fmri_mean4 = image.mean_img(fmri_vols4)
std_vols4 = image.math_img('np.std(img, axis=3)', img=fmri_vols4)
mean_data4 = masking.apply_mask(fmri_mean4, MASK_PATH[1])  # 1D array: voxel values
std_data4 = masking.apply_mask(std_vols4, MASK_PATH[1])


# Optional: plot histograms
plt.figure(figsize=(12,5))
plt.subplot(1,2,1)
plt.hist(mean_data1, bins=50, label='20° - No TOPUP')
plt.hist(mean_data2, bins=50, label='30° - No TOPUP',alpha=0.7)
plt.hist(mean_data3, bins=50, label='20° - TOPUP', color='yellow', alpha=0.5)
plt.hist(mean_data4, bins=50, label='30° - TOPUP', alpha=0.3)
plt.title('Histogram of Mean Signal (Brain Voxels)')
plt.xlabel('Mean Signal Intensity')
plt.ylabel('Voxel Count')
plt.legend()
plt.subplot(1,2,2)
plt.hist(std_data1, bins=50, label='20° - No TOPUP')
plt.hist(std_data2, bins=50, label='30° - No TOPUP',alpha=0.7)
plt.hist(std_data3, bins=50, label='20° - TOPUP', color='yellow', alpha=0.5)
plt.hist(std_data4, bins=50, label='30° - TOPUP', alpha=0.3)
plt.title('Histogram of Standard Deviation (Brain Voxels)')
plt.xlabel('Std of Signal Intensity')
plt.ylabel('Voxel Count')
plt.legend()
plt.tight_layout()
plt.show()

plt.figure(figsize=(12,5))
plt.hist(mean_data1/std_data1, bins=50, label='20° - TOPUP')
plt.hist(mean_data2/std_data2, bins=50, label='30° - TOPUP',alpha=0.7)
plt.hist(mean_data3/std_data3, bins=50, label='20° - No TOPUP', color='yellow', alpha=0.5)
plt.hist(mean_data4/std_data4, bins=50, label='30° - NoTOPUP',alpha=0.3)

plt.title('Histogram of tSNR (Brain Voxels)')
plt.xlabel('tSNR')
plt.ylabel('Voxel Count')
plt.legend()
plt.tight_layout()
plt.show()



# Plot img1 as a background (grayscale), and img2 as an overlay (color)
display = plotting.plot_anat(fmri_mean1, title="Overlay Comparison", draw_cross=False)
# Add the second image on top
display.add_overlay(fmri_mean2, cmap='jet', alpha=0.1)  # You can adjust alpha for transparency
plotting.show()


# Optional: plot histograms
plt.hist(mean_data1, bins=50)
plt.title('Histogram of Mean Signal (Brain Voxels)')
plt.xlabel('Signal Intensity')
plt.ylabel('Number of Voxels')
plt.show()

plt.hist(std_data2, bins=50)
plt.title('Histogram of Standard Deviation (Brain Voxels)')
plt.xlabel('Std of Signal Intensity')
plt.ylabel('Number of Voxels')
plt.show()