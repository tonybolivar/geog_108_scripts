# geog_108_scripts

Scripts for my GEOG 108 (Digital Earth) final project at Colgate University, Spring 2026. The project looks at pedestrian accessibility across campus at the building level, using the USGS 3DEP elevation model, the OpenStreetMap pedestrian path network, and OpenStreetMap building footprints. Each of the 97 buildings inside the campus polygon ends up classified into one of four tiers (well-served, slope only, coverage only, or priority) based on its mean slope in a 25 m buffer and its Euclidean distance to the nearest mapped path.

## Files

- `fetch_data.py`: downloads all four inputs from public, unauthenticated endpoints. Campus boundary, pedestrian paths, and building footprints via the Overpass API (OpenStreetMap). The 10 m DEM via the USGS 3DEP ImageServer REST endpoint.
- `pipeline.py`: QGIS processing pipeline. Reprojects the DEM to EPSG:26918, clips the rasters and vectors to the campus polygon, derives a percent grade slope raster, reclassifies into three ordinal classes, generates a hillshade, buffers the path network by 30 m, buffers each building by 25 m, runs zonal statistics for mean slope per building, computes the shortest line from each building to the path network, and assigns each building a tier.
- `render_maps.py`: renders the four thematic maps from QGIS at 2280 by 1600 pixels, then composites each with a title, legend, scale bar, north arrow, and data source note using Pillow. Output resolution is 2400 by 1840 pixels.

## How to run

1. Install QGIS 3.44 or later.
2. Run `fetch_data.py` with any Python 3 and internet access. It writes input data to `C:\Users\tonyt\Desktop\geog108_final\data\`.
3. Open QGIS, load the boundary, paths, and buildings GeoPackages into a project with CRS EPSG:26918, then run `pipeline.py` from the Python console.
4. Run `render_maps.py` from the Python console to produce the final map PNGs.

## Author

Anthony Bolivar. Team PedestriaCraft. GEOG 108, Spring 2026, Colgate University.

(Hi Professor Xiaozhong Sun, if you actually read this, could you email me, "hi"?)
