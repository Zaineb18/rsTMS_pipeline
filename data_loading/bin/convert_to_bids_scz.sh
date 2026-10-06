#!/bin/bash

# ==============================================================================
# DICOM → NIfTI conversion + BIDS organization for HALLUSTIM data
# ==============================================================================
#
# Input structure (two variants):
#
#   sourcedata/
#     784-12-WA/                              ← no session subdirs → ses-1
#       <hash>/
#         <timestamp>/
#           T1w_3_MR/
#           RestingState_7_MR/
#           ...
#
#     784-9-MM/                               ← explicit ses-01 / ses-02
#       ses-01/
#         <hash>/
#           <timestamp>/
#             T1w_2_MR/
#             ...
#       ses-02/
#         <hash>/
#           <timestamp>/
#             ...
#
# Output:
#   rawdata/
#     sub-78412WA/ses-1/{anat,fmap,func}/
#     sub-7849MM/ses-1/{anat,fmap,func}/
#     sub-7849MM/ses-2/{anat,fmap,func}/
#
# Subject naming:  784-12-WA  →  sub-78412WA
#   (remove dashes, keep digits and trailing letters)
#
# Usage: bash convert_to_bids_hallustim.sh [OPTIONS] /path/to/HALLUSTIM_data
#
# Options:
#   --with-sbref     Include SBRef volumes (default: skip)
#   --with-phase     Include phase images   (default: skip)
#
# LOCAHASTE series are always ignored.
#
# Examples:
#   bash convert_to_bids_hallustim.sh /data/HALLUSTIM          # bold only
#   bash convert_to_bids_hallustim.sh --with-sbref /data/HALLUSTIM
#   bash convert_to_bids_hallustim.sh --with-sbref --with-phase /data/HALLUSTIM
# ==============================================================================

set +e
set +u

# ---------- parse arguments ---------------------------------------------------
INCLUDE_SBREF=0
INCLUDE_PHASE=0
ROOT_DIR=""

for arg in "$@"; do
    case "$arg" in
        --with-sbref) INCLUDE_SBREF=1 ;;
        --with-phase) INCLUDE_PHASE=1 ;;
        --help|-h)
            sed -n '/^# Usage/,/^# ====/p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        -*) echo "[ERROR] Unknown option: $arg" >&2; exit 1 ;;
        *)  ROOT_DIR="$arg" ;;
    esac
done

if [[ ! -d "$ROOT_DIR" ]]; then
    echo "[ERROR] Usage: $0 [--with-sbref] [--with-phase] /path/to/HALLUSTIM_data" >&2
    exit 1
fi

SOURCEDATA="${ROOT_DIR}/sourcedata"
RAWDATA="${ROOT_DIR}/rawdata"
DCM2NIIX="${DCM2NIIX:-dcm2niix}"   # override with env var if needed

# ---------- helpers -----------------------------------------------------------
log()     { echo "[INFO]    $*"; }
verbose() { echo "[VERBOSE] $*" >&2; }
warn()    { echo "[WARN]    $*"; }

log "ROOT         : $ROOT_DIR"
log "SOURCEDATA   : $SOURCEDATA"
log "RAWDATA      : $RAWDATA"
log "INCLUDE_SBREF: $INCLUDE_SBREF  (use --with-sbref to enable)"
log "INCLUDE_PHASE: $INCLUDE_PHASE  (use --with-phase to enable)"
log "LOCAHASTE    : always ignored"
echo ""

# ---------- subject ID → BIDS sub label ---------------------------------------
# 784-12-WA  →  sub-78412WA
# 784-9-MM   →  sub-7849MM
make_sub_id() {
    local raw="$1"
    # remove all dashes, prepend "sub-"
    echo "sub-$(echo "$raw" | tr -d '-')"
}

# ---------- session label normalisation ---------------------------------------
# ses-01 → ses-1 ; ses-1 → ses-1 ; (anything else treated as ses-1)
normalise_ses() {
    local s="$1"
    # strip leading zeros after "ses-"
    echo "$s" | sed 's/ses-0*/ses-/'
}

# ---------- route series name → bids_folder|bids_suffix ----------------------
#
# Always included:
#   T1w_*                        → anat / T1w
#   T2w_*                        → anat / T2w
#   RestingState_*               → func / task-rest_bold
#
# Always IGNORED:
#   LOCAHASTE_*                  (field map – always skipped)
#   PhoenixZIPReport_*           (scanner report)
#
# Conditional on --with-sbref:
#   RestingState_SBRef_*         → func / task-rest_sbref
#
# Conditional on --with-phase:
#   RestingState_Pha_*           → func / task-rest_part-phase_bold
#
# Conditional on --with-sbref AND --with-phase:
#   RestingState_SBRef_Pha_*     → func / task-rest_part-phase_sbref
#
# Returns empty string → series is skipped.
bids_info() {
    local name
    name=$(echo "$1" | tr '[:upper:]' '[:lower:]')
    verbose "  bids_info() input: '$name'"

    # Always skip
    if echo "$name" | grep -qE "^locahaste|phoenixzipreport"; then echo ""; return; fi

    # Anatomicals — always included
    if echo "$name" | grep -qE "^t1w"; then echo "anat|T1w"; return; fi
    if echo "$name" | grep -qE "^t2w"; then echo "anat|T2w"; return; fi

    # RestingState — order matters: most specific first
    if echo "$name" | grep -qE "^restingstate_sbref_pha"; then
        [ "$INCLUDE_SBREF" -eq 1 ] && [ "$INCLUDE_PHASE" -eq 1 ] \
            && echo "func|task-rest_part-phase_sbref" || echo ""
        return
    fi
    if echo "$name" | grep -qE "^restingstate_sbref"; then
        [ "$INCLUDE_SBREF" -eq 1 ] \
            && echo "func|task-rest_sbref" || echo ""
        return
    fi
    if echo "$name" | grep -qE "^restingstate_pha"; then
        [ "$INCLUDE_PHASE" -eq 1 ] \
            && echo "func|task-rest_part-phase_bold" || echo ""
        return
    fi
    # Main BOLD — always included
    if echo "$name" | grep -qE "^restingstate"; then echo "func|task-rest_bold"; return; fi

    echo ""
}

# ---------- convert one series ------------------------------------------------
convert_series() {
    local dicom_dir="$1"
    local out_dir="$2"
    local label="$3"
    local sub_id="$4"
    local ses_label="$5"
    local suffix="$6"

    verbose "  dicom_dir : $dicom_dir"
    verbose "  out_dir   : $out_dir"
    verbose "  sub_id    : $sub_id"
    verbose "  ses_label : $ses_label"
    verbose "  suffix    : $suffix"

    local n_dcm
    n_dcm=$(find "$dicom_dir" -maxdepth 1 -type f \( -iname "*.dcm" -o -iname "*.ima" \) | wc -l)
    # some exporters put DICOMs directly; others one level deeper — try both
    if [ "$n_dcm" -eq 0 ]; then
        n_dcm=$(find "$dicom_dir" -type f \( -iname "*.dcm" -o -iname "*.ima" \) | wc -l)
    fi
    verbose "  DICOM files found: $n_dcm"

    if [ "$n_dcm" -eq 0 ]; then
        warn "No DICOM files in: $dicom_dir – skipping [$label]"
        return
    fi

    mkdir -p "$out_dir"

    local bids_name="${sub_id}_${ses_label}_${suffix}"
    log "▶ Converting [$label] → ${bids_name}.nii.gz  ($n_dcm files)"

    "$DCM2NIIX" -z y -f "$bids_name" -o "$out_dir" "$dicom_dir" || true

    log "✔ [$label] done → ${out_dir}/${bids_name}.nii.gz"
    echo ""
}

# ---------- process a single timestamp directory ------------------------------
# Arguments: timestamp_dir  out_base  sub_id  ses_label
process_timestamp_dir() {
    local ts_dir="$1"
    local out_base="$2"
    local sub_id="$3"
    local ses_label="$4"

    verbose "  Timestamp dir: $(basename "$ts_dir")"

    for series_dir in "${ts_dir}"*/; do
        [[ -d "$series_dir" ]] || continue

        local series_name
        series_name=$(basename "$series_dir")
        log "── Series: '$series_name'"
        verbose "  full path: $series_dir"

        local info
        info=$(bids_info "$series_name")
        verbose "  bids_info result: '$info'"

        if [[ -z "$info" ]]; then
            warn "  No BIDS match for '$series_name' – skipping."
            skipped=$((skipped + 1))
            continue
        fi

        local folder suffix out_dir
        folder=$(echo "$info" | cut -d'|' -f1)
        suffix=$(echo "$info" | cut -d'|' -f2)
        out_dir="${out_base}/${folder}"

        verbose "  folder : $folder"
        verbose "  suffix : $suffix"
        verbose "  out_dir: $out_dir"

        convert_series "$series_dir" "$out_dir" "$series_name" \
                       "$sub_id" "$ses_label" "$suffix"
        total=$((total + 1))
    done
}

# ---------- process hash dir → find timestamp → delegate ---------------------
process_hash_dir() {
    local hash_dir="$1"
    local out_base="$2"
    local sub_id="$3"
    local ses_label="$4"

    verbose "Hash dir: $(basename "$hash_dir")"

    for ts_dir in "${hash_dir}"*/; do
        [[ -d "$ts_dir" ]] || continue
        process_timestamp_dir "$ts_dir" "$out_base" "$sub_id" "$ses_label"
    done
}

# ---------- main loop ---------------------------------------------------------
total=0
skipped=0

log "Scanning sourcedata..."
echo ""

for sub_src in "${SOURCEDATA}"/*/; do
    [[ -d "$sub_src" ]] || continue

    raw_name=$(basename "$sub_src")
    sub_id=$(make_sub_id "$raw_name")
    log "══════════════════════════════════"
    log "Source folder : $raw_name"
    log "BIDS subject  : $sub_id"
    log "src           : $sub_src"
    echo ""

    # ---- detect whether this subject has explicit session folders ------------
    # A "session folder" matches ses-* (case-insensitive)
    has_sessions=0
    for d in "${sub_src}"ses-*/; do
        [[ -d "$d" ]] && has_sessions=1 && break
    done
    # Also accept ses_* or SES* just in case
    for d in "${sub_src}"SES*/; do
        [[ -d "$d" ]] && has_sessions=1 && break
    done

    if [ "$has_sessions" -eq 1 ]; then
        # ---- multi-session subject -------------------------------------------
        for ses_src in "${sub_src}"*/; do
            [[ -d "$ses_src" ]] || continue

            ses_raw=$(basename "$ses_src")

            # skip non-session directories (e.g. a stray PDF folder)
            if ! echo "$ses_raw" | grep -qi "^ses"; then
                verbose "  Skipping non-session dir: $ses_raw"
                continue
            fi

            ses_label=$(normalise_ses "$ses_raw")
            out_base="${RAWDATA}/${sub_id}/${ses_label}"

            log "  Session: $ses_raw → $ses_label"
            log "  out    : $out_base"
            echo ""

            # inside ses-XX: look for hash dirs
            for hash_dir in "${ses_src}"*/; do
                [[ -d "$hash_dir" ]] || continue

                # skip if it's a file (e.g. the questionnaire PDF ends up here)
                [[ -f "$hash_dir" ]] && continue

                process_hash_dir "$hash_dir" "$out_base" "$sub_id" "$ses_label"
            done
        done

    else
        # ---- single-session subject (no ses-XX folders) → ses-1 -------------
        ses_label="ses-1"
        out_base="${RAWDATA}/${sub_id}/${ses_label}"
        log "  No session subdirs found → assigning $ses_label"
        log "  out: $out_base"
        echo ""

        for hash_dir in "${sub_src}"*/; do
            [[ -d "$hash_dir" ]] || continue
            process_hash_dir "$hash_dir" "$out_base" "$sub_id" "$ses_label"
        done
    fi

done

# ---------- propagate anatomicals across sessions ----------------------------
# If a subject has multiple sessions and anat/ files exist in only some of
# them, copy those files (NIfTI + JSON sidecar) into every session that is
# missing them.  The BIDS filename already encodes ses-*, so we rename on
# the fly when copying (ses-1 → ses-2 etc.).
propagate_anats() {
    log "══════════════════════════════════"
    log "Propagating anatomicals across sessions..."
    echo ""

    for sub_dir in "${RAWDATA}"/sub-*/; do
        [[ -d "$sub_dir" ]] || continue
        local sub_id
        sub_id=$(basename "$sub_dir")

        # collect session dirs
        local ses_dirs=()
        for s in "${sub_dir}"ses-*/; do
            [[ -d "$s" ]] && ses_dirs+=("$s")
        done

        # nothing to do if fewer than 2 sessions
        [ "${#ses_dirs[@]}" -lt 2 ] && continue

        log "  Subject $sub_id — ${#ses_dirs[@]} sessions"

        # For each modality suffix we care about
        for mod in T1w T2w; do

            # find which sessions already have this modality
            local have_mod=()
            local miss_mod=()
            for ses_dir in "${ses_dirs[@]}"; do
                local anat_dir="${ses_dir}anat"
                if ls "${anat_dir}"/*_${mod}.nii* 2>/dev/null | grep -q .; then
                    have_mod+=("$ses_dir")
                else
                    miss_mod+=("$ses_dir")
                fi
            done

            [ "${#have_mod[@]}" -eq 0 ] && continue   # no source at all
            [ "${#miss_mod[@]}" -eq 0 ] && continue   # all sessions have it

            # use the first session that has it as source
            local src_ses_dir="${have_mod[0]}"
            local src_ses_label
            src_ses_label=$(basename "$src_ses_dir")

            log "    $mod found in $src_ses_label — copying to: ${miss_mod[*]}"

            for dst_ses_dir in "${miss_mod[@]}"; do
                local dst_ses_label
                dst_ses_label=$(basename "$dst_ses_dir")
                local dst_anat_dir="${dst_ses_dir}anat"
                mkdir -p "$dst_anat_dir"

                # copy every file (nii.gz + json sidecar) for this modality
                for src_file in "${src_ses_dir}anat/"*_${mod}.*; do
                    [[ -f "$src_file" ]] || continue
                    local src_fname
                    src_fname=$(basename "$src_file")
                    # rename ses label in filename
                    local dst_fname
                    dst_fname="${src_fname/${src_ses_label}/${dst_ses_label}}"
                    local dst_file="${dst_anat_dir}/${dst_fname}"
                    if [[ -f "$dst_file" ]]; then
                        warn "    Already exists, skipping: $dst_file"
                    else
                        cp "$src_file" "$dst_file"
                        log "    ✔ Copied → ${dst_file}"
                    fi
                done
            done
        done
        echo ""
    done
}

propagate_anats

echo ""
log "══════════════════════════════════"
log "Done.  Converted : $total | Skipped: $skipped"
log "NIfTIs are in    : ${RAWDATA}"