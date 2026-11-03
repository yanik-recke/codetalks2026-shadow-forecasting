#!/bin/bash
# Calculates a shadow raster for every day/time with r.sun.
# Don't run this directly, it has to run inside GRASS. Use run_in_grass.sh:
#
#   ./run_in_grass.sh /path/to/dsm.tif /path/to/shadows
#
# Each result is written to <OUTPUT_DIR>/<day>_<time>.tif where all shadows
# have the value 1 and everything else is 'No data'. 06_make_tiles.py picks
# these up and turns them into tiles.

set -e

DSM="$1"
OUTPUT_DIR="$2"

# Days of the year (1 - 365) and local solar time in decimal hours (8.5 = 8:30)
DAY_START=${DAY_START:-184}
DAY_END=${DAY_END:-184}
TIME_START=${TIME_START:-8}
TIME_END=${TIME_END:-20}
TIME_STEP=${TIME_STEP:-0.5}

mkdir -p "$OUTPUT_DIR"

r.import --overwrite input="$DSM" output=dsm
g.region raster=dsm -p

for d in $(seq "$DAY_START" "$DAY_END"); do
    for t in $(seq "$TIME_START" "$TIME_STEP" "$TIME_END" | awk '{printf "%.1f\n", $1}'); do
        start_time=$(date +%s)

        # To speed this up, pre-compute the horizons once before the loop with
        #   r.horizon elevation=dsm step=5 output=horizon
        # and add this to r.sun: horizon_basename=horizon horizon_step=5
        # (aspect/slope layers can be computed with r.slope.aspect and passed as aspect=/slope=)
        r.sun --overwrite elevation=dsm day="$d" time="$t" incidout=incidout

        # Every value that is not null (0 - 999) becomes 'No data', every 'No data' becomes 1
        # -> all shadows have the value 1
        r.null map=incidout setnull=0-999 null=1

        # Export to a temporary file first and then move it, so 06_make_tiles.py
        # never picks up a file that is only half written
        r.out.gdal --overwrite --quiet -c input=incidout output="$OUTPUT_DIR/.export.tif" format=GTiff
        mv "$OUTPUT_DIR/.export.tif" "$OUTPUT_DIR/${d}_${t}.tif"

        echo "Day $d, $t took $(( $(date +%s) - start_time ))s"
    done
done
