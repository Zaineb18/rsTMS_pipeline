# logging_utils.py
from params import *
import os, sys
import numpy as np
import pandas as pd
from datetime import datetime

# ── constants ───────────────────────────────────────────────────────────────
W  = 68          # width of inner separator lines
IND = "    "     # 4-space indent used everywhere


# ── Tee ─────────────────────────────────────────────────────────────────────
class Tee:
    def __init__(self, filepath):
        self._terminal = sys.stdout
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self._file = open(filepath, 'a')
        self._file.write(f"\n{'#'*60}\n"
                         f"# Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                         f"{'#'*60}\n")
    def write(self, message):
        self._terminal.write(message)
        self._file.write(message)
    def flush(self):
        self._terminal.flush()
        self._file.flush()
    def restore(self):
        self._file.close()
        return self._terminal


# ── layout helpers ───────────────────────────────────────────────────────────
def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def subsection(title):
    print(f"\n  ··· {title} ···")


def _sep():
    """Inner separator aligned with IND."""
    print(f"{IND}{'─'*W}")


def _row(label, value, unit="", label_w=48, val_w=10):
    """Single aligned data row: label · value · unit."""
    if isinstance(value, float):
        val_str = f"{value:>{val_w}.4f}"
    elif isinstance(value, int):
        val_str = f"{value:>{val_w}}"
    else:
        val_str = f"{str(value):>{val_w}}"
    unit_str = f"  {unit}" if unit else ""
    print(f"{IND}  {label:<{label_w}} {val_str}{unit_str}")


def _row1(label, value, unit="", label_w=48, val_w=10):
    """Single aligned data row with 1 decimal place."""
    val_str = f"{value:>{val_w}.1f}"
    unit_str = f"  {unit}" if unit else ""
    print(f"{IND}  {label:<{label_w}} {val_str}{unit_str}")


def _row2(label, value, unit="", label_w=48, val_w=10):
    """Single aligned data row with 2 decimal places."""
    val_str = f"{value:>{val_w}.2f}"
    unit_str = f"  {unit}" if unit else ""
    print(f"{IND}  {label:<{label_w}} {val_str}{unit_str}")


def _xyz(label, coord, label_w=40, val_w=8, fmt=".2f"):
    """XYZ coordinate row."""
    fmt_str = f":>{val_w}{fmt}"
    vals = "  ".join(f"{v:{fmt_str[1:]}}" for v in coord)
    print(f"{IND}  {label:<{label_w}} {vals}")


def _comment(text):
    """Explanatory comment line, indented under a row."""
    print(f"{IND}    ↳ {text}")


# ── log_section (used before the optimisation runs) ─────────────────────────
def log_section(title, rows, width_label=50, width_val=10, unit_col=True):
    section(title)
    _sep()
    for row in rows:
        label  = row['label']
        values = row['values']
        if not isinstance(values, (list, tuple, np.ndarray)):
            values = [values]
        values_str = "  ".join(
            f"{v:>{width_val}.2f}" if isinstance(v, float) else f"{v:>{width_val}}"
            for v in values
        )
        unit_str = f"  {row['unit']}" if unit_col and 'unit' in row else ""
        print(f"{IND}  {label:<{width_label}} {values_str}{unit_str}")
    _sep()


# ── E-field block ────────────────────────────────────────────────────────────
def _print_efield_block(title, description, metrics, di_dt_real, MSO):
    """
    Print one E-field metrics block with inline explanation of every metric.
    All rows use identical indentation (IND + 2 spaces) and column widths.
    """
    section(title)
    print(f"{IND}  Elements : {description}")
    _sep()

    # |E| max over GM surface
    print(f"\n{IND}  |E| max over GM surface  (reference)")
    _comment("max(magnE) over all tag 1002 triangles")
    _row("|E| max over GM", metrics['e_max_gm'], "V/m")

    # |E| at cortical target
    print(f"\n{IND}  |E| at cortical target  [primary clinical metric]")
    _comment("Σ(w_i · magnE_i) / Σ(w_i)  over elements where Target > 0")
    _comment("w_i = Target mask value (currently 1 everywhere, centered on tms_opt.target)")
    _row("|E| at target (weighted mean)", metrics['e_at_target'], "V/m")

    # Focus ratio
    print(f"\n{IND}  Focus ratio")
    _comment("|E| at target / |E| max over GM")
    _comment("Fraction of the GM peak field delivered to the intended target")
    _comment("1.0 = field peak exactly at target  |  0 = no field at target")
    _row2("ratio", metrics['e_ratio'])

    # Distribution
    print(f"\n{IND}  Distribution of magnE over target elements (Target mask > 0)")
    _row ("  n elements in target region",  metrics['n_nodes_in_target'], "elements")
    _row ("  mean (unweighted)",            metrics['e_mean'],            "V/m")
    _row ("  median",                       metrics['e_median'],           "V/m")
    _row ("  std",                          metrics['e_std'],              "V/m")
    print(f"{IND}  {'  IQR  (Q25 – Q75)':<48} "
          f"{metrics['e_p25']:>10.4f} – {metrics['e_p75']:.4f}  V/m")
    _comment("Narrow IQR → homogeneous field across target")
    _comment("Wide IQR   → strong spatial gradient across target")

    # Scaled to real MSO
    e_real = metrics['e_at_target'] * di_dt_real
    print(f"\n{IND}  Scaled to real pulse intensity")
    _comment(f"|E| at target × dI/dt  =  {metrics['e_at_target']:.4f} V/m  ×  {di_dt_real:.0f} A/µs")
    _comment(f"SimNIBS normalises to 1 A/µs; MagVenture Cool-B65 at {MSO}% MSO ≈ {di_dt_real:.0f} A/µs")
    _row2(f"|E| at target at {MSO}% MSO", e_real, "V/m")
    _comment("Clinical threshold: ~100 V/m for cortical activation")
    if e_real < 50:
        print(f"{IND}    ⚠  {e_real:.1f} V/m — target likely too deep, consider increasing MSO.")
    elif e_real >= 100:
        print(f"{IND}    ✓  {e_real:.1f} V/m — target within stimulable range.")
    else:
        print(f"{IND}    ~  {e_real:.1f} V/m — borderline, verify with clinician.")

    _sep()


# ── results summary ──────────────────────────────────────────────────────────
def print_results_summary(opt_pos, tms_opt, mni_coords, nearest_gm_coord, nearest_gm_dist,
                          nearest_scalp_coord, scalp_to_target_mm, mni_to_subj_displacement,
                          efield_gm, efield_shell, di_dt_per_MSO=1.2, MSO=100, Occip=False,
                          toward_occip=None, toward_front=None, optim_orientation=True,
                          fn=None, subject=None, session=None):

    section("RESULTS SUMMARY")
    coil_centre       = np.squeeze(opt_pos)[:3, 3]
    coil_to_target_mm = float(np.linalg.norm(coil_centre - tms_opt.target))

    # ── Coordinates ──────────────────────────────────────────────────────────
    print(f"\n{IND}  {'Space / point':<40}  {'x':>8}  {'y':>8}  {'z':>8}   (mm)")
    _sep()
    _xyz("MNI (standard space)",              mni_coords,          fmt="d")
    _xyz("Target — subject T1w",              tms_opt.target)
    _xyz("Nearest GM node (CHARM mesh)",      nearest_gm_coord)
    _xyz("Nearest scalp node (CHARM mesh)",   nearest_scalp_coord)
    if not optim_orientation:
        ref_mni = toward_occip if Occip else toward_front
        _xyz("pos_ydir — MNI",                ref_mni,             fmt="d")
        _xyz("pos_ydir — subject T1w",        tms_opt.pos_ydir)
    _xyz("Coil centre (opt_pos[:3, 3])",      coil_centre)
    _sep()

    # ── Distances ─────────────────────────────────────────────────────────────
    print(f"\n{IND}  {'Distance':<48}  {'value':>8}   unit")
    _sep()
    distances = [
        ("MNI → subject T1w displacement",
         mni_to_subj_displacement,
         "mm", "nonlinear warp  T^-1·p_MNI,  expected 10–25 mm"),
        ("target → nearest GM node",
         nearest_gm_dist,
         "mm", "sanity check — should be < 5 mm"),
        ("target → scalp  (d_scalp)",
         scalp_to_target_mm,
         "mm", "stimulation depth inside head"),
        ("coil above scalp  (tms_opt.distance)",
         tms_opt.distance,
         "mm", "SimNIBS default coil–scalp air gap"),
        ("total coil → target  (estimated)",
         scalp_to_target_mm + tms_opt.distance,
         "mm", "d_scalp + air gap"),
        ("coil → target  TRUE",
         coil_to_target_mm,
         "mm", "||opt_pos[:3,3] - tms_opt.target||_2"),
    ]
    for label, val, unit, comment in distances:
        _row1(label, val, unit)
        _comment(comment)
    _sep()

    # ── E-field blocks ────────────────────────────────────────────────────────
    di_dt_real = di_dt_per_MSO * MSO

    _print_efield_block(
        title       = "E-field metrics — full GM volume  (tag 2 tetrahedra)",
        description = "all GM volume tetrahedra (tag 2), includes deep GM elements",
        metrics     = efield_gm,
        di_dt_real  = di_dt_real,
        MSO         = MSO,
    )

    _print_efield_block(
        title       = "E-field metrics — GM surface shell  (tag 2 within 1 mm of tag 1002)",
        description = "tag 2 elements within 1 mm of tag 1002 — superficial cortical layer",
        metrics     = efield_shell,
        di_dt_real  = di_dt_real,
        MSO         = MSO,
    )

    # ── Localite file ─────────────────────────────────────────────────────────
    subsection("Localite output file")
    if fn:
        print(f"{IND}  {fn}")
    if subject and session:
        print(f"\n{'█'*60}")
        print(f"█  END  —  sub-{subject}  ses-{session}")
        print(f"{'█'*60}\n")
