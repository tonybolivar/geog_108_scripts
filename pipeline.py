import os

import processing
from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsField,
    QgsFillSymbol,
    QgsLineSymbol,
    QgsPalettedRasterRenderer,
    QgsProject,
    QgsRasterLayer,
    QgsRendererCategory,
    QgsSingleSymbolRenderer,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor


DATA = r"C:\Users\tonyt\Desktop\geog108_final\data"
CRS = "EPSG:26918"


def reproject_raster(src, out, res=3):
    processing.run(
        "gdal:warpreproject",
        {
            "INPUT": src,
            "SOURCE_CRS": "EPSG:4326",
            "TARGET_CRS": CRS,
            "RESAMPLING": 1,
            "TARGET_RESOLUTION": res,
            "DATA_TYPE": 6,
            "OUTPUT": out,
        },
    )


def clip_raster(src, mask, out):
    processing.run(
        "gdal:cliprasterbymasklayer",
        {
            "INPUT": src,
            "MASK": mask,
            "TARGET_CRS": CRS,
            "NODATA": 0,
            "CROP_TO_CUTLINE": False,
            "KEEP_RESOLUTION": True,
            "OUTPUT": out,
        },
    )


def compute_slope(dem, out):
    processing.run(
        "gdal:slope",
        {
            "INPUT": dem,
            "BAND": 1,
            "SCALE": 1.0,
            "AS_PERCENT": True,
            "COMPUTE_EDGES": True,
            "OUTPUT": out,
        },
    )


def reclassify_slope(slope_pct, out):
    processing.run(
        "native:reclassifybytable",
        {
            "INPUT_RASTER": slope_pct,
            "RASTER_BAND": 1,
            "TABLE": [0, 5, 1, 5, 10, 2, 10, 1000, 3],
            "NO_DATA": 0,
            "RANGE_BOUNDARIES": 0,
            "NODATA_FOR_MISSING": True,
            "DATA_TYPE": 0,
            "OUTPUT": out,
        },
    )


def compute_hillshade(dem, out):
    processing.run(
        "gdal:hillshade",
        {
            "INPUT": dem,
            "BAND": 1,
            "Z_FACTOR": 1.0,
            "AZIMUTH": 315.0,
            "ALTITUDE": 45.0,
            "COMPUTE_EDGES": True,
            "OUTPUT": out,
        },
    )


def buffer_vector(src, distance, out, dissolve=False):
    processing.run(
        "native:buffer",
        {
            "INPUT": src,
            "DISTANCE": distance,
            "SEGMENTS": 8,
            "DISSOLVE": dissolve,
            "END_CAP_STYLE": 0,
            "JOIN_STYLE": 0,
            "OUTPUT": out,
        },
    )


def zonal_mean(zones, raster, out, prefix="slope_"):
    processing.run(
        "native:zonalstatisticsfb",
        {
            "INPUT": zones,
            "INPUT_RASTER": raster,
            "RASTER_BAND": 1,
            "COLUMN_PREFIX": prefix,
            "STATISTICS": [2],
            "OUTPUT": out,
        },
    )


def shortest_line(source, destination, out):
    processing.run(
        "native:shortestline",
        {
            "SOURCE": source,
            "DESTINATION": destination,
            "METHOD": 0,
            "NEIGHBORS": 1,
            "DISTANCE": 1e9,
            "OUTPUT": out,
        },
    )


def assign_tier(slope_mean, dist_path, steep=10, reach=30):
    if slope_mean is None:
        return "well"
    is_steep = slope_mean > steep
    is_sparse = dist_path > reach
    if is_steep and is_sparse:
        return "both"
    if is_steep:
        return "slope"
    if is_sparse:
        return "cov"
    return "well"


def tier_buildings(buildings_path, out_path):
    layer = QgsVectorLayer(buildings_path, "buildings", "ogr")
    fields = [f.name() for f in layer.fields()]
    if "tier" not in fields:
        layer.startEditing()
        layer.addAttribute(QgsField("tier", QVariant.String, len=8))
        layer.updateFields()
        layer.commitChanges()

    layer.startEditing()
    idx = layer.fields().indexOf("tier")
    for feat in layer.getFeatures():
        layer.changeAttributeValue(
            feat.id(),
            idx,
            assign_tier(feat["slope_mean"], feat["dist_path"]),
        )
    layer.commitChanges()

    processing.run(
        "native:savefeatures",
        {
            "INPUT": layer,
            "OUTPUT": out_path,
        },
    )


def run():
    boundary = os.path.join(DATA, "boundary_26918.gpkg")
    paths_clip = os.path.join(DATA, "paths_clip.gpkg")
    buildings_campus = os.path.join(DATA, "buildings_campus.gpkg")

    dem_raw = os.path.join(DATA, "dem_3dep.tif")
    dem_utm = os.path.join(DATA, "dem_26918.tif")
    reproject_raster(dem_raw, dem_utm)

    slope_pct = os.path.join(DATA, "slope_pct.tif")
    compute_slope(dem_utm, slope_pct)

    slope_class = os.path.join(DATA, "slope_class.tif")
    reclassify_slope(slope_pct, slope_class)

    hs = os.path.join(DATA, "hillshade.tif")
    compute_hillshade(dem_utm, hs)

    clip_raster(slope_class, boundary, os.path.join(DATA, "slope_class_clip.tif"))
    clip_raster(hs, boundary, os.path.join(DATA, "hillshade_clip.tif"))

    paths_buf30 = os.path.join(DATA, "paths_buf30.gpkg")
    buffer_vector(paths_clip, 30, paths_buf30, dissolve=True)

    buildings_buf25 = os.path.join(DATA, "buildings_buf25.gpkg")
    buffer_vector(buildings_campus, 25, buildings_buf25, dissolve=False)

    buildings_slope = os.path.join(DATA, "buildings_with_slope.gpkg")
    zonal_mean(buildings_buf25, slope_pct, buildings_slope)

    dist_lines = os.path.join(DATA, "building_to_path_lines.gpkg")
    shortest_line(buildings_campus, paths_clip, dist_lines)

    print("Pipeline complete. Run tier_buildings() next with a merged buildings layer")
    print("that has both slope_mean and dist_path attributes joined.")


if __name__ == "__main__" or True:
    run()
