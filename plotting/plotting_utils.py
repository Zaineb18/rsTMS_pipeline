from nilearn import plotting
import nibabel as nib
import matplotlib.pyplot as plt 
from nilearn import datasets, surface, plotting 
from nilearn.surface import load_surf_mesh
from scipy.spatial import cKDTree

def disp_bold_with_masks_and_seeds(mean_func,mpath,output_file,radius_mm = 10, coords=[(6,16,-10)],title="mean cleaned bold - MNI space: -30°"):
    disp = plotting.plot_img(
        mean_func,
        cut_coords=coords,
        title=title,
        cmap="gray"
        )
    marker_size = radius_mm / 0.35  # Convert mm to points
    disp.add_contours(nib.load(mpath))
    disp.add_markers(coords, marker_color='red', marker_size=marker_size)
    disp.savefig(output_file)  # Save the figure
    plotting.show()

def plot_sgc_signal(tc, sgc_mask, sgc_mask_noncl,output_file,):
    plt.figure(figsize=(20,5))
    plt.plot(tc, sgc_mask_noncl, label='before cleaning')
    plt.plot(tc, sgc_mask, label='after cleaning')
    plt.title('Mean signal fluctuation over SGC seed',fontsize=20)
    plt.ylabel('Signal intensity (a.u)', fontsize=15)
    plt.xlabel('Time (s)', fontsize=15)
    plt.xticks(size=10)
    plt.yticks(size=10)
    plt.savefig(output_file, bbox_inches='tight')  # Save the figure
    plt.legend(fontsize=15)  

def disp_connectivity(z_img, roi_img, output_file, title="Seed-based SGC functional connectivity over brain mask", coords=(-44,40,29)):
    disp = plotting.plot_stat_map(
        z_img,
        title=title,
        cmap="cold_hot",
        cut_coords=coords)
    disp.add_contours(roi_img)
    disp.savefig(output_file)  # Save the figure
    plotting.show()

def disp_roi(roi_img, mean_func,output_file,title="DLPFC ROI (summed seeds)",coords=(-36, 39, 43) ):
    plotting.plot_roi(roi_img, bg_img=mean_func, title=title, cut_coords=coords)
    plotting.show()


def project_on_surf(correlation_map, hemi,threshold, title, output_file, mni_coord):
    fsaverage = datasets.fetch_surf_fsaverage()    
    
    if hemi=="left":
        surf_coords, _ = load_surf_mesh(fsaverage.pial_left)
        tree = cKDTree(surf_coords)
        _, idx = tree.query(mni_coord)
        surf_point = surf_coords[idx]
        texture = surface.vol_to_surf(correlation_map, fsaverage.pial_left)
        disp = plotting.plot_surf(
                fsaverage.infl_left,
                texture,
                hemi='left',
                title=title, colorbar=True,
                threshold=threshold, bg_map=fsaverage.sulc_left)
        #disp.add_markers([surf_point], marker_color='red', marker_size=30)
        disp.savefig(output_file)  # Save the figure

                
    if hemi=="right":
        texture = surface.vol_to_surf(correlation_map, fsaverage.pial_right)
        disp = plotting.plot_surf(
                fsaverage.infl_right, texture, hemi='right',
                title=title, colorbar=True,
                threshold=threshold, bg_map=fsaverage.sulc_right)
        disp.savefig(output_file)  # Save the figure       
    plotting.show()          