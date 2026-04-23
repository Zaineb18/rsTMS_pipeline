#!/usr/bin/env bash
# Usage: ./anonymize_subject.sh <dataset_path> <subject_id>
# Example: ./anonymize_subject.sh /path/to/dataset sub-RASger

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <dataset_path> <subject_id>"
    exit 1
fi

DATASET_PATH="$1"
SUBJECT_ID="$2"
SOURCEDATA="${DATASET_PATH}/sourcedata/${SUBJECT_ID}/ses-1"

if [[ ! -d "$SOURCEDATA" ]]; then
    echo "ERROR: sourcedata directory not found: $SOURCEDATA"
    exit 1
fi

echo "Processing subject: $SUBJECT_ID"
echo "Sourcedata path: $SOURCEDATA"
echo ""

# Both structures end in an MR/ leaf directory:
#   Structure A: ses-1/<hash>/<series name>/Unknown Study/MR/
#   Structure B: ses-1/<series name>/Unknown Study/MR/
mapfile -t DICOM_DIRS < <(find "$SOURCEDATA" -type d -name "MR")

if [[ ${#DICOM_DIRS[@]} -eq 0 ]]; then
    echo "No MR directories found under $SOURCEDATA"
    exit 1
fi

echo "Found ${#DICOM_DIRS[@]} MR director(y/ies) to anonymize:"
for d in "${DICOM_DIRS[@]}"; do
    echo "  $d"
done
echo ""

for DICOM_DIR in "${DICOM_DIRS[@]}"; do
    echo "Anonymizing: $DICOM_DIR"
    dicom-anonymizer "$DICOM_DIR" "$DICOM_DIR"
    echo "  Done."
done

echo ""
echo "Anonymization complete for $SUBJECT_ID."