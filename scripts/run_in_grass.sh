#!/bin/bash
# Starts GRASS with a temporary EPSG:25832 project and runs 05_calc_shadows.sh in it.
#
#   ./run_in_grass.sh /path/to/dsm.tif /path/to/shadows
#
# Days and times can be changed via environment variables, e.g.:
#
#   DAY_START=180 DAY_END=210 TIME_START=9 TIME_END=21 ./run_in_grass.sh dsm.tif shadows
#
# Since every run gets its own temporary GRASS project, you can run several of
# these at the same time, e.g. one per area.

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <dsm.tif> <output-dir>"
    exit 1
fi

# Path to GRASS, change this if yours is somewhere else (on Linux it's usually just "grass")
GRASS=${GRASS:-/Applications/GRASS-8.4.app/Contents/MacOS/Grass.sh}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DSM="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
mkdir -p "$2"
OUTPUT_DIR="$(cd "$2" && pwd)"

export DAY_START DAY_END TIME_START TIME_END TIME_STEP
"$GRASS" --tmp-project EPSG:25832 --exec bash "$SCRIPT_DIR/05_calc_shadows.sh" "$DSM" "$OUTPUT_DIR"
