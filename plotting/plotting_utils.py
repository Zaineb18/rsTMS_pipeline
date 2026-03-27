from nilearn import plotting
import nibabel as nib
import matplotlib.pyplot as plt 
from nilearn import datasets, surface, plotting 
from nilearn.surface import load_surf_mesh
from scipy.spatial import cKDTree
import os
import numpy as np
import matplotlib.gridspec as gridspec
from nilearn.image import clean_img
from nilearn.image import math_img


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

def disp_connectivity(z_img, roi_img, min_mni_coord,output_file, title="Seed-based SGC functional connectivity over brain mask", coords=(-44,40,29)):
    disp = plotting.plot_stat_map(
        z_img,
        title=title,
        cmap="cold_hot",
        cut_coords=coords)
    disp.add_contours(roi_img)
    if min_mni_coord is not None:
        coord = tuple(np.round(min_mni_coord).astype(int))
        disp.add_markers(
            [coord],
            marker_color="green",
            marker_size=30,)
        for ax in disp.axes.values():
            ax.ax.annotate(
                f"x={coord[0]}, y={coord[1]}, z={coord[2]}",
                xy=(0.02, 0.05),
                xycoords="axes fraction",
                fontsize=20,
                color="pink",
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="black", alpha=0.6),
            )
            break
    disp.savefig(output_file)  # Save the figure
    plotting.show()

def disp_roi(roi_img, mean_func,output_file,title="DLPFC ROI (summed seeds)",coords=(-36, 39, 43) ):
    plotting.plot_roi(roi_img, bg_img=mean_func, title=title, cut_coords=coords)
    plotting.show()


def project_on_surf(correlation_map, hemi,threshold, title, output_file, mni_coord, min_mni_coord=None):
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
                cmap="cold_hot",
                threshold=threshold, bg_map=fsaverage.sulc_left)
        disp.savefig(output_file)  # Save the figure
                
    if hemi=="right":
        texture = surface.vol_to_surf(correlation_map, fsaverage.pial_right)
        disp = plotting.plot_surf(
                fsaverage.infl_right, texture, hemi='right',
                title=title, colorbar=True, cmap="cold_hot",
                threshold=threshold, bg_map=fsaverage.sulc_right)
        disp.savefig(output_file)  # Save the figure       
    plotting.show()
    disp.savefig(output_file)
    plotting.show()

def add_targets(display, ind_coord, std_coord, ind_size=80, std_size=80):
    display.add_markers([ind_coord], marker_color="green", marker_size=ind_size, marker="o")
    display.add_markers([std_coord], marker_color="purple", marker_size=std_size, marker="*")
    return display
def stat_view(disp, ax, cut_coords, title, correlation_img, mean_func, ind_coord, std_coord):
    disp = plotting.plot_stat_map(
        correlation_img, bg_img=mean_func,
        cut_coords=cut_coords,
        display_mode="ortho", cmap="cold_hot", symmetric_cbar=True,
        colorbar=True, threshold=0.0, axes=ax, title=title,
    )
    add_targets(disp, ind_coord, std_coord)  # FIX: was add_targets(disp)
    return disp

def plot_target_comparison(min_mni_coord, correlation_img, mean_func, output_dir,
                           tissue, stat, subj, ses, standard_coord=(-46, 46, 36)):
    ind_coord = tuple(np.round(min_mni_coord).astype(int))
    std_coord = tuple(standard_coord)
    distance_mm = np.linalg.norm(np.array(ind_coord) - np.array(std_coord))
    #correlation_img = math_img("np.nan_to_num(img)", img=correlation_img)    
    fig = plt.figure(figsize=(18, 10))
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)
    title_base = (f"Individual {ind_coord}  vs  Standard {std_coord}\n"
                  f"sub-{subj} - ses-{ses}\n[{tissue} - {stat}]")
    fig.suptitle(title_base, fontsize=12, fontweight="bold")
    ax1 = fig.add_subplot(gs[0, 0])
    glass_disp = plotting.plot_glass_brain(
        correlation_img, display_mode="lyrz", colorbar=True,
        cmap="cold_hot", symmetric_cbar=True, threshold=0.0,
        axes=ax1, title="Glass brain (SGC connectivity)",)
    add_targets(glass_disp, ind_coord, std_coord, 120, 120)
    ax2 = fig.add_subplot(gs[0, 1])
    display = stat_view(None, ax2, ind_coord, f"Individual target {ind_coord}",
                        correlation_img, mean_func, ind_coord, std_coord)
    ax4 = fig.add_subplot(gs[1, 1])
    display = stat_view(None, ax4, std_coord, f"Standard target {std_coord}",
                        correlation_img, mean_func, ind_coord, std_coord)
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.axis("off")
    summary_text = (
        f"TARGET COMPARISON SUMMARY\n"
        f"{'─'*32}\n\n"
        f"Individual (green ●): {ind_coord}\n"
        f"Standard Fox et al. (purple ★): {std_coord}\n"
        #f"Euclidean distance: {distance_mm:.1f} mm\n"
        #f"Axis breakdown:\n"
        #f"Δx = {abs(ind_coord[0]-std_coord[0])} mm  "
        #f"Δy = {abs(ind_coord[1]-std_coord[1])} mm  "
        #f"Δz = {abs(ind_coord[2]-std_coord[2])} mm\n"
        )
    ax3.text(0.05, 0.95, summary_text, transform=ax3.transAxes,
             fontsize=15, verticalalignment="top", fontfamily="monospace",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.85))
    vol_path = os.path.join(output_dir,
        f"sub-{subj}_ses-{ses}_target-comparison-vol_{stat}map-{tissue}.png")
    fig.savefig(vol_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return distance_mm