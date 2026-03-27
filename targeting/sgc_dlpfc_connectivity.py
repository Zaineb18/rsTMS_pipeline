from rsTMS_pipeline.data_loading.params import *
from rsTMS_pipeline.data_loading.loading_utils import *
from rsTMS_pipeline.preproc.preproc_utils import *
from rsTMS_pipeline.targeting.targeting_utils import *
from rsTMS_pipeline.plotting.plotting_utils import *
from nilearn.image import mean_img, load_img, clean_img,index_img
import pandas as pd

# ==========================
# Seed-based SGC–DLPFC Functional Connectivity for Individualized TMS Targeting
#
# Author: Zaineb Amor
#
# Context:
#   TMS treatment efficacy in MDD is maximized when stimulation targets the
#   DLPFC site most anticorrelated with the subgenual cingulate cortex (SGC)
#   at rest (Fox et al., Biol Psychiatry 2012; Fox et al., JAMA Psychiatry 2013).
#   This script implements that individualized targeting pipeline on
#   fMRIPrep-preprocessed, denoised resting-state BOLD data.
#
#   For each subject and session, it computes a whole-brain SGC seed-based
#   connectivity map, restricts it to a DLPFC ROI, and identifies the voxel
#   with the minimum (most anticorrelated) connectivity value. That coordinate
#   is the recommended individualized TMS target, and is compared against the
#   Fox group-level standard coordinate (-46, 46, 36).
#
#   Two connectivity metrics are computed in parallel:
#     - Pearson r map (raw correlation)
#     - Fisher z map (r-to-z transformed, more statistically appropriate)
#   Two tissue masks are applied to the DLPFC ROI:
#     - Brain mask (whole brain, first-pass estimate)
#     - GM mask (grey matter only, recommended final target)
#
# This script loops over all subjects and sessions. For each, it:
#
# --- Step 1: Load fMRIPrep outputs ---
#
#   Calls load_fmriprepdata() to retrieve paths for the given subject,
#   session, and MNI space:
#     - Denoised BOLD functional image(s)
#     - Brain mask(s)
#     - Confounds TSV sidecar(s)  [loaded for completeness, not reused here]
#     - Preprocessed T1w anatomical image
#     - Grey matter (GM) probability segmentation map from fMRIPrep
#
# --- Step 2: Detect and handle multi-run sessions ---
#
#   Checks whether BOLD filenames contain a 'run-XX' BIDS entity.
#   If present, BOLD, mask, and confounds lists are sorted by run index
#   via sort_by_run(), guaranteeing correct triplet pairing across runs.
#   Single-run sessions are handled transparently.
#
# --- Step 3: Denoise and compute mean BOLD ---
#
#   For each (BOLD, mask, confounds) triplet:
#     1. Calls clean_bold() to regress out motion and WM/CSF confounds
#        and detrend (see preproc_utils.py).
#     2. Saves a mean BOLD QC figure with the SGC seed coordinate (6,16,-10)
#        marked in red and the brain mask contour overlaid.
#
# --- Step 4: SGC seed-based connectivity map ---
#
#   Defines a 10 mm spherical seed centred on the SGC (MNI: 6, 16, -10),
#   following Fox et al. 2012. Extracts the mean seed time series and
#   computes voxelwise Pearson correlation across the whole brain via
#   sgc_coorelation_map(), which returns both:
#     - correlation_img : Pearson r map (Nifti1Image)
#     - z_img           : Fisher z-transformed map (Nifti1Image)
#       computed as z = arctanh(r), clipped to [-0.9999, 0.9999] to
#       avoid divergence at perfect (anti)correlation.
#
# --- Step 5: DLPFC ROI construction ---
#
#   Builds a binary DLPFC ROI by unioning three 15 mm spheres centred on
#   coordinates from the Fox 2013 target region:
#     (-36, 39, 43), (-44, 40, 29), (-41, 16, 54).
#   The union is binarised and used to restrict the connectivity maps.
#   A QC figure of the ROI overlaid on the mean BOLD is saved.
#
# --- Step 6: Identify optimal TMS target ---
#
#   Iterates over two connectivity metrics (stat) and two tissue masks
#   (tissue), yielding four target estimates per run:
#
#   Stats:
#     'pearson'  — uses raw Pearson r map (correlation_img)
#     'fisherz'  — uses Fisher z map (z_img); preferred for group comparison
#
#   Tissues:
#     'brainmask' — restricts DLPFC ROI to whole-brain mask via
#                   min_target_roi(). First-pass estimate.
#     'gmmask'    — further restricts to GM voxels (probability > 0.5)
#                   via min_target_gm(). Recommended final clinical target,
#                   as TMS acts on cortical grey matter.
#
#   In all cases, the voxel with the minimum connectivity value (maximum
#   SGC anticorrelation) within the masked ROI is identified as the
#   individualized target, per Fox et al. 2012.
#
#   If no anticorrelated voxel is found (min value >= 0), min_target_*
#   falls back to the Fox group-level coordinate (-46, 46, 36) and prints
#   a warning.
#
# --- Step 7: Visualize and save outputs ---
#
#   For each (stat × tissue) combination, three figures are saved:
#
#   1. disp_connectivity() — axial/coronal/sagittal stat map with:
#        - DLPFC ROI contour overlaid
#        - Individualized target marked as a lime green dot
#        - MNI coordinates printed on the figure
#      Cuts are centred on the individualized target coordinate.
#
#   2. project_on_surf() — left hemisphere surface projection of the
#      connectivity map with the individualized target marked.
#
#   3. plot_target_comparison() — 4-panel figure comparing the
#      individualized target against the Fox standard (-46, 46, 36):
#          - Glass brain with both seeds
#          - Stat map centred on individual target
#          - Stat map centred on standard target
#          - Summary text: coordinates, Euclidean distance, axis breakdown
#
# --- Step 8: Save targeting results to TSV ---
#
#   After all (stat × tissue) iterations for a given run, calls
#   save_targeting_results() with the accumulated results list.
#   This writes a single tab-separated file per run containing one row
#   per (stat × tissue) combination, with the following fields:
#     - BIDS identifiers: subject, session, run
#     - Connectivity metric and tissue mask used
#     - Individualized MNI target coordinates (x, y, z)
#     - Connectivity value at the target (min_connectivity; should be negative)
#     - Fox standard coordinate (std_x, std_y, std_z)
#     - Euclidean distance to standard (distance_mm)
#     - Per-axis displacement (delta_x/y/z_mm)
#     - Fallback flag (used_fallback = True if no anticorrelated voxel
#       was found and the Fox coordinate was substituted)
#
#   The recommended value for neuronavigation is the row where
#   stat='Fisher Z' and tissue='GM mask', as this combines the most
#   statistically appropriate connectivity metric with the most
#   anatomically precise tissue restriction.
#
# --- Step 9: Memory management ---
#
#   Intermediate per-iteration variables (masked_conn_img, min_voxel_idx,
#   min_z_value, min_mni_coord) are explicitly deleted after each
#   (stat × tissue) iteration to prevent memory accumulation across
#   the subject/session/run loops.
#
# Notes:
#   - Run the denoising script before this one; clean_bold() outputs must
#     exist on disk or be recomputed here via the clean_bold() call.
#   - The GM map (gm_file) is loaded once per session and reused across
#     all runs and tissue iterations within that session.
#   - The anticorrelated target coordinate from the 'gmmask' + 'fisherz'
#     combination is the most statistically grounded estimate and the
#     value recommended for neuronavigation.
#   - Euclidean distance between the individualized and standard targets
#     is printed and displayed on figures for each combination.
#
# References:
#   Fox MD et al. (2012). Clinical cortical stimulation and resting-state
#     functional connectivity. Biol Psychiatry, 71(12), 1067–1074.
#   Fox MD et al. (2013). Efficacy of TMS targets for depression is related
#     to intrinsic functional connectivity with the subgenual cingulate.
#     Biol Psychiatry, 72(7), 595–603.
# ==========================

tissues = {'brainmask': 'brain mask', 'gmmask': 'GM mask'}
stats = {'pearson':'Person Correlation', 'fisherz':'Fisher Z'}
std_coord = (-46, 46, 36)
for subj in subjects: 
    for ses in sessions: 
        print('SUBJECT:', subj, '- SESSION:', ses)
        FUNC_PATH, MASK_PATH, CONFOUNDS_PATH, ANAT_PATH, GM_PATH = load_fmriprepdata(FMRIPREP_PATH, subj, ses, space)
        
        bold_files = FUNC_PATH
        mask_files = MASK_PATH
        confounds_files = CONFOUNDS_PATH
        anat_files = ANAT_PATH   
        gm_file = GM_PATH      
        # Detect whether run labels exist in filenames
        func_has_runs = any(re.search(r'run-(\d+)', f) for f in bold_files)
        multi_run = func_has_runs
        if multi_run:
            bold_files = sort_by_run(bold_files)
            mask_files = sort_by_run(mask_files)
            confounds_files = sort_by_run(confounds_files)
        anat = image.load_img(anat_files)
       
        for func_f, mask_f, confounds_f in zip(bold_files, mask_files, confounds_files):
            clean_func, mean_func, sample_mask, confounds = clean_bold(func_f, confounds_f,mask_f, tr=1.09)
            os.makedirs(os.path.join(FIGS_PATH, f'sub-{subj}/ses-{ses}'), exist_ok=True)            
            os.makedirs(os.path.join(RES_PATH, f'sub-{subj}/ses-{ses}'), exist_ok=True)
            
            disp = plotting.plot_img(mean_func,cut_coords=(6,16,-10),title=f'sub-{subj} - ses-{ses} \nmean BOLD',cmap="gray")
            disp.add_contours(nib.load(mask_f))
            disp.add_markers([(6,16,-10)], marker_color='red', marker_size=30)
            disp.savefig(os.path.join(FIGS_PATH, f'sub-{subj}/ses-{ses}', f'sub-{subj}_ses-{ses}_meanbold.png'))
            plotting.show()
            
            sgc_masker,sgc_mask,sgc_mask_noncl = sgc_masking(clean_func,radius_mm=10,seeds_sgc = [(6,16,-10)])
            correlation_img, correlation_map, z_img, z_map = sgc_coorelation_map(mask_f, clean_func, sgc_mask,)
            roi_data, roi_img=dlpfc_masking(clean_func,mask_f,seeds_dlpfc = [(-36,39,43), (-44,40,29), (-41,16,54)])
            disp_roi(roi_img, mean_func,os.path.join(FIGS_PATH, f'sub-{subj}/ses-{ses}', 'sub-{subj}_ses-{ses}_roidlpfc.png'),
                     title=f'sub-{subj} - ses-{ses} \nDLPFC ROI (summed seeds)',coords=(-44,40,29)) 
            
            results = []
            for stat in stats.keys():
                if stat == 'pearson':
                    conn_img = correlation_img
                elif stat == 'fisherz':
                    conn_img = z_img    
                for tissue in tissues.keys():
                    if tissue == 'brainmask':
                        masked_conn_img, min_voxel_idx, min_z_value, min_mni_coord = min_target_roi(conn_img, roi_img)
                    elif tissue == 'gmmask':  
                        masked_conn_img, min_voxel_idx, min_z_value, min_mni_coord = min_target_gm(conn_img, roi_img,gm_file)
                    
                    disp_connectivity(masked_conn_img, roi_img,  min_mni_coord,
                    output_file= os.path.join(FIGS_PATH, f'sub-{subj}/ses-{ses}', f'sub-{subj}_ses-{ses}_{stats[stat]}map-{tissue}.png'),
                    title=f'sub-{subj} - ses-{ses} \nSeed-based SGC functional connectivity over {tissues[tissue]}\n{stats[stat]}', 
                    coords=min_mni_coord)
                    project_on_surf(masked_conn_img, hemi='left',threshold=0.0,
                    title=f'sub-{subj} - ses-{ses} \nSeed-based SGC functional connectivity over {tissues[tissue]}\n{stats[stat]}',
                    output_file = os.path.join(FIGS_PATH, f'sub-{subj}/ses-{ses}', f'sub-{subj}_ses-{ses}_{stats[stat]}surf-{tissue}.png'),
                    mni_coord=(-44,40,29), min_mni_coord=min_mni_coord)
                    distance_mm = plot_target_comparison(min_mni_coord=min_mni_coord,correlation_img=masked_conn_img,mean_func=mean_func,
                    output_dir=os.path.join(FIGS_PATH, f'sub-{subj}/ses-{ses}'),tissue=tissues[tissue], stat=stats[stat], 
                    subj=subj,ses=ses,standard_coord=std_coord)
                    
                    coord = tuple(np.round(min_mni_coord).astype(int))
                    results.append({
                            'subject':          subj,
                            'session':          ses,
                            'run':              re.search(r'run-(\d+)', func_f).group(0) if re.search(r'run-(\d+)', func_f) else 'run-01',
                            'stat':             stats[stat],
                            'tissue':           tissues[tissue],
                            'mni_x':            coord[0],
                            'mni_y':            coord[1],
                            'mni_z':            coord[2],
                            'min_connectivity': float(np.round(min_z_value, 4)),
                            'std_x':            std_coord[0],
                            'std_y':            std_coord[1],
                            'std_z':            std_coord[2],
                            'distance_mm':      float(np.round(distance_mm, 2)),
                            'delta_x_mm':       abs(coord[0] - std_coord[0]),
                            'delta_y_mm':       abs(coord[1] - std_coord[1]),
                            'delta_z_mm':       abs(coord[2] - std_coord[2]),
                            'used_fallback':    min_voxel_idx is None,
                        })                  
                    
                    del(masked_conn_img, min_voxel_idx, min_z_value, min_mni_coord)
            df_run, csv_path = save_targeting_results(results, subj, ses, output_dir=os.path.join(RES_PATH, f'sub-{subj}/ses-{ses}'))