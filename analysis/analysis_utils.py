from scipy.spatial import cKDTree
import numpy as np

def compute_efield_metrics(m_res, gm_shell=False, shell_mm=1.0):
    """
    Compute E-field metrics from a SimNIBS result mesh.

    All fields are ElementData (per tetrahedron or triangle).
    SimNIBS tissue tags: WM=1, GM=2, CSF=3, skull=4, scalp=5
                         GM surface triangles = 1002

    e_max_gm   : np.max of magnE over tag 1002 triangles (GM surface).
                 Tag 1002 is what the SimNIBS viewer renders.
                 True peak — viewer clips for display but metric uses true max.

    e_at_target: weighted mean of magnE over elements where Target > 0,
                 using Target mask values as weights.
                 Target mask is a Gaussian weight (0→1) centered on
                 tms_opt.target. Weighted mean gives the typical field
                 at the cortical target, de-emphasising peripheral elements.
                 Always ≤ e_max_gm so ratio is always in [0, 1].

    e_ratio    : e_at_target / e_max_gm
                 Focus metric: fraction of the GM peak field delivered
                 to the target. 1.0 = field peak is exactly at target.
    """
    all_target = m_res.field['Target'].value   # (n_elements,) Gaussian weight mask
    all_magnE  = m_res.field['magnE'].value    # (n_elements,) |E| in V/m

    # e_max_gm: true peak over GM surface triangles (tag 1002)
    # computed once, independent of gm_shell — always the same reference
    gm_surf_mask    = m_res.elm.tag1 == 1002
    gm_surf_indices = np.where(gm_surf_mask)[0]
    e_max_gm = float(np.max(all_magnE[gm_surf_indices])) \
               if len(gm_surf_indices) > 0 else float('nan')

    # Select tag 2 (GM volume tetrahedra) elements for target statistics
    gm_vol_mask    = m_res.elm.tag1 == 2
    gm_vol_indices = np.where(gm_vol_mask)[0]

    if gm_shell:
        # Restrict to tag 2 elements within shell_mm of tag 1002 surface
        # — approximates the superficial cortical layer visible in the viewer
        gm_vol_nodes      = m_res.elm.node_number_list[gm_vol_mask] - 1       # (n_vol, 4)
        gm_vol_centroids  = m_res.nodes.node_coord[gm_vol_nodes].mean(axis=1) # (n_vol, 3)
        gm_surf_nodes     = m_res.elm.node_number_list[gm_surf_mask][:, :3] - 1
        gm_surf_centroids = m_res.nodes.node_coord[gm_surf_nodes].mean(axis=1)
        surf_tree         = cKDTree(gm_surf_centroids)
        dists_to_surf, _  = surf_tree.query(gm_vol_centroids, k=1)
        shell_mask        = dists_to_surf <= shell_mm
        selected_indices  = gm_vol_indices[shell_mask]
    else:
        selected_indices  = gm_vol_indices

    target_sel      = all_target[selected_indices]
    magnE_sel       = all_magnE[selected_indices]
    in_target       = target_sel > 0
    magnE_in_target = magnE_sel[in_target]
    weights         = target_sel[in_target]   # Gaussian Target mask values as weights

    if len(magnE_in_target) == 0:
        print(f"  WARNING: no target elements found (gm_shell={gm_shell})")
        nan = float('nan')
        return {k: nan for k in
                ['e_at_target', 'e_max_gm', 'e_ratio', 'e_mean_w', 'e_mean',
                 'e_median', 'e_std', 'e_p25', 'e_p75', 'n_nodes_in_target']}

    # e_at_target = weighted mean using Target mask as weights
    e_at_target = float(np.average(magnE_in_target, weights=weights))
    e_ratio     = e_at_target / e_max_gm if e_max_gm > 0 else float('nan')
    e_mean      = float(np.mean(magnE_in_target))
    e_median    = float(np.median(magnE_in_target))
    e_std       = float(np.std(magnE_in_target))
    e_p25       = float(np.percentile(magnE_in_target, 25))
    e_p75       = float(np.percentile(magnE_in_target, 75))
    n_nodes     = int(np.sum(in_target))

    if gm_shell:
        print(f"  [shell] n_shell={shell_mask.sum()}, n_in_target={n_nodes}, "
              f"e_max_tag1002={e_max_gm:.4f}, "
              f"e_at_target(weighted_mean)={e_at_target:.4f}")

    return {
        'e_at_target':       e_at_target,
        'e_max_gm':          e_max_gm,
        'e_ratio':           e_ratio,
        'e_mean_w':          e_at_target,   # alias kept for log compatibility
        'e_mean':            e_mean,
        'e_median':          e_median,
        'e_std':             e_std,
        'e_p25':             e_p25,
        'e_p75':             e_p75,
        'n_nodes_in_target': n_nodes,
    }