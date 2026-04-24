import json
import os
import sys
import urllib.parse
import urllib.request

DATA = r"C:\Users\tonyt\Desktop\geog108_final\data"
os.makedirs(DATA, exist_ok=True)

SOUTH, WEST, NORTH, EAST = 42.803, -75.553, 42.825, -75.527

OVERPASS = "https://overpass-api.de/api/interpreter"


def overpass(query):
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(
        OVERPASS,
        data=data,
        headers={"User-Agent": "pedestriacraft/1.0"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def osm_to_geojson(osm, geom_filter=None):
    features = []
    for el in osm.get("elements", []):
        if el["type"] == "way" and "geometry" in el:
            coords = [[n["lon"], n["lat"]] for n in el["geometry"]]
            is_closed = len(coords) >= 4 and coords[0] == coords[-1]
            tags = el.get("tags", {})
            if is_closed and (geom_filter in (None, "polygon")):
                geom = {"type": "Polygon", "coordinates": [coords]}
            else:
                geom = {"type": "LineString", "coordinates": coords}
            features.append({
                "type": "Feature",
                "id": el["id"],
                "properties": tags,
                "geometry": geom,
            })
        elif el["type"] == "relation" and "members" in el:
            outer_rings = []
            for m in el.get("members", []):
                if m.get("role") == "outer" and "geometry" in m:
                    coords = [[n["lon"], n["lat"]] for n in m["geometry"]]
                    if len(coords) >= 4 and coords[0] != coords[-1]:
                        coords.append(coords[0])
                    if len(coords) >= 4:
                        outer_rings.append(coords)
            if outer_rings:
                if len(outer_rings) == 1:
                    geom = {"type": "Polygon", "coordinates": outer_rings}
                else:
                    geom = {
                        "type": "MultiPolygon",
                        "coordinates": [[r] for r in outer_rings],
                    }
                features.append({
                    "type": "Feature",
                    "id": el["id"],
                    "properties": el.get("tags", {}),
                    "geometry": geom,
                })
    return {"type": "FeatureCollection", "features": features}


def write_geojson(path, fc):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fc, f)
    print(f"  wrote {path}  features={len(fc['features'])}")


def fetch_campus_boundary():
    print("[1/4] Campus boundary (Overpass)")
    q = """
    [out:json][timeout:60];
    (
      relation["name"="Colgate University"](area);
      way["name"="Colgate University"];
      relation["name"="Colgate University"];
    );
    out geom;
    """
    osm = overpass(q)
    fc = osm_to_geojson(osm)
    write_geojson(os.path.join(DATA, "campus_boundary.geojson"), fc)


def fetch_paths():
    print("[2/4] Pedestrian paths (Overpass)")
    q = f"""
    [out:json][timeout:120][bbox:{SOUTH},{WEST},{NORTH},{EAST}];
    (
      way["highway"="footway"];
      way["highway"="steps"];
      way["highway"="path"];
      way["highway"="pedestrian"];
    );
    out geom;
    """
    osm = overpass(q)
    fc = osm_to_geojson(osm, geom_filter="line")
    for f in fc["features"]:
        if f["geometry"]["type"] == "Polygon":
            ring = f["geometry"]["coordinates"][0]
            f["geometry"] = {"type": "LineString", "coordinates": ring}
    write_geojson(os.path.join(DATA, "paths.geojson"), fc)


def fetch_buildings():
    print("[3/4] Buildings (Overpass)")
    q = f"""
    [out:json][timeout:120][bbox:{SOUTH},{WEST},{NORTH},{EAST}];
    (
      way["building"];
      relation["building"];
    );
    out geom;
    """
    osm = overpass(q)
    fc = osm_to_geojson(osm, geom_filter="polygon")
    write_geojson(os.path.join(DATA, "buildings_bbox.geojson"), fc)


def fetch_dem():
    print("[4/4] 3DEP DEM (USGS ImageServer)")
    url = (
        "https://elevation.nationalmap.gov/arcgis/rest/services/"
        "3DEPElevation/ImageServer/exportImage"
    )
    params = {
        "bbox": f"{WEST},{SOUTH},{EAST},{NORTH}",
        "bboxSR": "4326",
        "imageSR": "4326",
        "size": "2048,1800",
        "format": "tiff",
        "pixelType": "F32",
        "noData": "-9999",
        "interpolation": "RSP_BilinearInterpolation",
        "f": "image",
    }
    full = url + "?" + urllib.parse.urlencode(params)
    out = os.path.join(DATA, "dem_3dep.tif")
    req = urllib.request.Request(full, headers={"User-Agent": "pedestriacraft/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r, open(out, "wb") as f:
        f.write(r.read())
    sz = os.path.getsize(out)
    print(f"  wrote {out}  bytes={sz}")


def main():
    fetch_campus_boundary()
    fetch_paths()
    fetch_buildings()
    fetch_dem()
    print("\nInputs written to", DATA)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
