#!/bin/bash

# ==============================================================================
# DICOM → NIfTI conversion + BIDS organization for rTMS_data
# ==============================================================================
# Input  : sourcedata/sub-*/ses-*/<hash>/<series>/
# Output : rawdata/sub-*/ses-1/{anat,fmap,func}/
#
# Usage  : bash convert_to_bids.sh /media/zaineb/Data/rTMS_data
# ==============================================================================

set +e
set +u

# ---------- argument ----------------------------------------------------------
ROOT_DIR="${1}"
if [[ ! -d "$ROOT_DIR" ]]; then
    echo "[ERROR] Usage: $0 /path/to/rTMS_data" >&2
    exit 1
fi

SOURCEDATA="${ROOT_DIR}/sourcedata"
RAWDATA="${ROOT_DIR}/rawdata"

# ---------- helpers -----------------------------------------------------------
log()     { echo "[INFO]    $*"; }
verbose() { echo "[VERBOSE] $*" >&2; }
warn()    { echo "[WARN]    $*"; }

log "ROOT      : $ROOT_DIR"
log "SOURCEDATA: $SOURCEDATA"
log "RAWDATA   : $RAWDATA"
echo ""

# ---------- route series name → folder|suffix ---------------------------------
bids_info() {
    local name
    name=$(echo "$1" | tr '[:upper:]' '[:lower:]')
    verbose "  bids_info() input: '$name'"
    if   echo "$name" | grep -q "t1";    then echo "anat|T1w"
    elif echo "$name" | grep -q "t2";    then echo "anat|T2w"
    elif echo "$name" | grep -q "invpe"; then echo "fmap|dir-PA_epi"
    elif echo "$name" | grep -q "bold";  then echo "func|task-restingstate_bold"
    else echo ""
    fi
}

# ---------- convert one series ------------------------------------------------
convert_series() {
    local dicom_dir="$1"
    local out_dir="$2"
    local label="$3"
    local sub_id="$4"
    local suffix="$5"

    verbose "  dicom_dir : $dicom_dir"
    verbose "  out_dir   : $out_dir"
    verbose "  sub_id    : $sub_id"
    verbose "  suffix    : $suffix"

    local n_dcm
    n_dcm=$(find "$dicom_dir" -type f \( -iname "*.dcm" -o -iname "*.ima" \) | wc -l)
    verbose "  DICOM files found: $n_dcm"

    if [ "$n_dcm" -eq 0 ]; then
        warn "No DICOM files in: $dicom_dir – skipping [$label]"
        return
    fi

    mkdir -p "$out_dir"

    local bids_name="${sub_id}_ses-1_${suffix}"
    log "▶ Converting [$label] → ${bids_name}.nii.gz  ($n_dcm files)"

    cd /home/team/
    ./dcm2niix -z y -f "$bids_name" -o "$out_dir" "$dicom_dir" || true

    log "✔ [$label] done → ${out_dir}/${bids_name}.nii.gz"
    echo ""
}

# ---------- main loop ---------------------------------------------------------
total=0
skipped=0

log "Scanning sourcedata..."
echo ""

for sub_src in "${SOURCEDATA}"/sub-*/; do
    [[ ! -d "$sub_src" ]] && continue

    sub_id=$(basename "$sub_src")
    out_base="${RAWDATA}/${sub_id}/ses-1"

    log "══════════════════════════════════"
    log "Subject : $sub_id"
    log "src     : $sub_src"
    log "out     : $out_base"
    echo ""

    for ses_dir in "${sub_src}"ses-*/; do
        [[ ! -d "$ses_dir" ]] && continue
        verbose "Session dir: $(basename "$ses_dir")"

        for hash_dir in "${ses_dir}"*/; do
            [[ ! -d "$hash_dir" ]] && continue
            verbose "Hash dir: $(basename "$hash_dir")"

            for series_dir in "${hash_dir}"*/; do
                [[ ! -d "$series_dir" ]] && continue

                series_name=$(basename "$series_dir")
                log "── Series: '$series_name'"
                verbose "  full path: $series_dir"

                info=$(bids_info "$series_name")
                verbose "  bids_info result: '$info'"

                if [[ -z "$info" ]]; then
                    warn "  No BIDS match for '$series_name' – skipping."
                    skipped=$((skipped + 1))
                    continue
                fi

                folder=$(echo "$info" | cut -d'|' -f1)
                suffix=$(echo "$info" | cut -d'|' -f2)
                out_dir="${out_base}/${folder}"

                verbose "  folder : $folder"
                verbose "  suffix : $suffix"
                verbose "  out_dir: $out_dir"

                # Check if DICOMs are directly in series_dir or one level deeper
                n_dcm_direct=$(find "$series_dir" -maxdepth 1 -type f \( -iname "*.dcm" -o -iname "*.ima" \) | wc -l)

                if [ "$n_dcm_direct" -gt 0 ]; then
                    # DICOMs sit directly in the series folder
                    convert_series "$series_dir" "$out_dir" "$series_name" "$sub_id" "$suffix"
                    total=$((total + 1))
                else
                    # DICOMs are inside a study subdirectory (e.g. "Unknown Study/")
                    found_study=0
                    for study_dir in "${series_dir}"*/; do
                        [[ ! -d "$study_dir" ]] && continue
                        verbose "  Study dir: $(basename "$study_dir")"
                        convert_series "$study_dir" "$out_dir" "$series_name" "$sub_id" "$suffix"
                        total=$((total + 1))
                        found_study=$((found_study + 1))
                    done

                    if [ "$found_study" -eq 0 ]; then
                        warn "  No DICOM files or study subdirectory found under: $series_dir"
                        skipped=$((skipped + 1))
                    fi
                fi

            done
        done
    done
done

echo ""
log "══════════════════════════════════"
log "Done.  Converted : $total | Skipped: $skipped"
log "NIfTIs are in    : ${RAWDATA}"