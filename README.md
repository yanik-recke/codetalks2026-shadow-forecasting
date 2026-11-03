# Shadow Forecasting Scripts

Scripts from my code.talks 2026 talk *Shadow Forecasting Using Publicly
Available City Models and Data*. All the context, the datasets and the
step-by-step explanation are on [codetalks.schattenpause.de](https://codetalks.schattenpause.de).

They are not the most polished scripts, but they work. All coordinates are in
`EPSG:25832`, which is what Hamburg's data uses.

## What you need

- [QGIS](https://qgis.org/) (I used the LTR version) with the GRASS tools
- [GRASS GIS](https://grass.osgeo.org/) for `run_in_grass.sh`
- Python 3 with `rasterio` and `shapely` for `01_find_elevation_tiles.py`:
  `pip install -r requirements.txt`

## The scripts, in the order I used them

| Script | Runs in | What it does |
|---|---|---|
| `01_find_elevation_tiles.py` | Terminal | Finds the elevation tiles that intersect your area and copies them into a folder. Merge them with `gdal_merge.py -o terrain.tif out/*.tif` |
| `02_find_buildings.py` | Terminal | Finds the CityGML files that intersect your area and copies them into a folder |
| `03_merge_citygml.py` | QGIS Python console | Merges all loaded CityGML layers into one (fixes the "field too long" error) |
| `04_filter_trees.py` | Terminal | Cuts the street tree register down to your area |
| `05_calc_shadows.sh` + `run_in_grass.sh` | Terminal (GRASS) | Calculates a shadow raster for every day/time with `r.sun` |
| `06_make_tiles.py` | QGIS Python console | Turns the shadow rasters into map tiles, while `05` is still running |
| `05_calc_shadows_qgis.py` | QGIS Python console | Alternative to `05` + `06` that does everything inside QGIS. Fine for a few points in time, but slower |

Between `04` and `05` you build the digital surface model (terrain + buildings
+ trees) in QGIS. That part is manual, the steps are described on the website.

## Example

```bash
# Example area: Ottensen
python scripts/01_find_elevation_tiles.py ~/data/dgm1 out/tiles 560000 5933000 563000 5935000
gdal_merge.py -o terrain.tif out/tiles/*.tif

python scripts/02_find_buildings.py ~/data/lod2 out/buildings 560000 5933000 563000 5935000
python scripts/04_filter_trees.py ~/data/trees.json out/trees.geojson 560000 5933000 563000 5935000

# ... build dsm.tif in QGIS ...

# July 3rd (day 184), every 30 minutes from 8:00 to 20:00
DAY_START=184 DAY_END=184 ./scripts/run_in_grass.sh dsm.tif out/shadows
```

Then open `06_make_tiles.py` in the QGIS Python console, set `INPUT_DIR` to
`out/shadows` and run it.

## Good to know

- `r.sun` uses **local solar time**, not the time on your watch. In Hamburg,
  solar noon is around 13:20 in summer (CEST), so you have to shift your times
  accordingly.
- Every `run_in_grass.sh` run uses its own temporary GRASS project, so you can
  run several areas at the same time.
- If you want to use aspect and slope layers, there is a GRASS tool that
  computes both from your DSM: `r.slope.aspect` (also available in the QGIS
  Processing Toolbox).
- The calculations can be sped up by pre-computing the horizons once with the
  GRASS tool `r.horizon` and passing them to `r.sun`. Computing them takes a
  while (about 20 minutes for Ottensen), so it's mainly worth it when you
  calculate a lot of days/times for the same area. In QGIS you can pass them
  to `r.sun.incidout` as well (`HORIZON` in `05_calc_shadows_qgis.py`):

  ```bash
  r.horizon elevation=dsm step=5 output=horizon
  r.sun elevation=dsm day=184 time=14 incidout=incidout horizon_basename=horizon horizon_step=5
  ```
- On a Mac, the Python that QGIS uses is under
  `/Applications/QGIS-LTR.app/Contents/MacOS/bin/` (or `QGIS.app` if you have
  the regular version). Use its `pip` to install packages you want to use in
  the QGIS Python console.
