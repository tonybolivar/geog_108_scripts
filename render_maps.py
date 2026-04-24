import os

from PIL import Image, ImageDraw, ImageFont
from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsFillSymbol,
    QgsLineSymbol,
    QgsMapRendererParallelJob,
    QgsMapSettings,
    QgsPalettedRasterRenderer,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsRendererCategory,
    QgsSimpleLineSymbolLayer,
    QgsSingleSymbolRenderer,
    QgsUnitTypes,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QEventLoop, QSize
from qgis.PyQt.QtGui import QColor


OUT_DIR = r"C:\Users\tonyt\Desktop\geog108_maps\final"
BASE_DIR = r"C:\Users\tonyt\Desktop\geog108_maps\v2"
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(BASE_DIR, exist_ok=True)

F_TITLE = r"C:\Windows\Fonts\georgiab.ttf"
F_SANS = r"C:\Windows\Fonts\segoeui.ttf"
F_SANS_B = r"C:\Windows\Fonts\segoeuib.ttf"
F_SANS_I = r"C:\Windows\Fonts\segoeuii.ttf"

C_BG = (248, 245, 238)
C_GREEN = (31, 75, 46)
C_INK = (42, 42, 42)
C_MUTE = (107, 107, 107)
C_CARDBOR = (200, 193, 178)
C_PRI = (176, 58, 46)

CW, CH = 2400, 1840
MAP_W, MAP_H = 2280, 1600
MAP_X, MAP_Y = 60, 120


def find(name):
    for layer in QgsProject.instance().mapLayers().values():
        if layer.name() == name:
            return layer
    return None


def build_map_extent(boundary_layer):
    ext = boundary_layer.extent()
    target_aspect = MAP_W / MAP_H
    cx = (ext.xMinimum() + ext.xMaximum()) / 2
    cy = (ext.yMinimum() + ext.yMaximum()) / 2
    h = ext.height() * 1.06
    w = h * target_aspect
    return QgsRectangle(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), w


def render_layers(layers, out_name, map_extent):
    ms = QgsMapSettings()
    ms.setLayers(layers)
    ms.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:26918"))
    ms.setExtent(map_extent)
    ms.setOutputSize(QSize(MAP_W, MAP_H))
    ms.setBackgroundColor(QColor("#F8F5EE"))
    job = QgsMapRendererParallelJob(ms)
    job.start()
    loop = QEventLoop()
    job.finished.connect(loop.quit)
    loop.exec_()
    out_path = os.path.join(BASE_DIR, out_name)
    job.renderedImage().save(out_path, "PNG")
    return out_path


def style_layers():
    slope = find("Slope classes (clipped)")
    if slope:
        classes = [
            QgsPalettedRasterRenderer.Class(1, QColor("#FEE6A0"), "Flat (<5%)"),
            QgsPalettedRasterRenderer.Class(2, QColor("#F3A057"), "Moderate (5-10%)"),
            QgsPalettedRasterRenderer.Class(3, QColor("#B83A2B"), "Steep (>10%)"),
        ]
        slope.setRenderer(QgsPalettedRasterRenderer(slope.dataProvider(), 1, classes))
        slope.setOpacity(0.88)

    path_buf = find("Path Coverage (30m buffer)")
    if path_buf:
        sym = QgsFillSymbol.createSimple(
            {"color": "156, 184, 154, 170", "outline_style": "no"}
        )
        path_buf.setRenderer(QgsSingleSymbolRenderer(sym))

    paths = find("OSM Paths")
    if paths:
        psym = QgsLineSymbol.createSimple(
            {
                "line_color": "42,42,42,255",
                "line_width": "0.45",
                "line_width_unit": "MM",
                "capstyle": "round",
                "joinstyle": "round",
            }
        )
        paths.setRenderer(QgsSingleSymbolRenderer(psym))

    boundary = find("Campus Boundary")
    if boundary:
        sym = QgsFillSymbol()
        while sym.symbolLayerCount() > 0:
            sym.deleteSymbolLayer(0)
        halo = QgsSimpleLineSymbolLayer()
        halo.setColor(QColor("#FFFFFF"))
        halo.setWidth(1.8)
        halo.setWidthUnit(QgsUnitTypes.RenderMillimeters)
        sym.appendSymbolLayer(halo)
        core = QgsSimpleLineSymbolLayer()
        core.setColor(QColor("#1F4B2E"))
        core.setWidth(0.9)
        core.setWidthUnit(QgsUnitTypes.RenderMillimeters)
        sym.appendSymbolLayer(core)
        boundary.setRenderer(QgsSingleSymbolRenderer(sym))

    buildings = find("Buildings by accessibility tier")
    if buildings:
        def tier_sym(fill, stroke, stroke_w):
            return QgsFillSymbol.createSimple(
                {
                    "color": fill,
                    "outline_color": stroke,
                    "outline_width": stroke_w,
                    "outline_width_unit": "MM",
                }
            )

        cats = [
            QgsRendererCategory("well", tier_sym("#D9D6CC", "#6F6E6A", "0.2"), "Well-served (60)"),
            QgsRendererCategory("slope", tier_sym("#D9A74A", "#7C5A1C", "0.3"), "Slope only (21)"),
            QgsRendererCategory("cov", tier_sym("#5E85A3", "#2A4258", "0.3"), "Coverage only (10)"),
            QgsRendererCategory("both", tier_sym("#B03A2E", "#4A0F08", "0.6"), "Priority (6)"),
        ]
        buildings.setRenderer(QgsCategorizedSymbolRenderer("tier", cats))

    hillshade = find("Hillshade (clipped)")
    if hillshade:
        hillshade.setOpacity(0.35)


def font(path, size):
    return ImageFont.truetype(path, size)


def make_canvas():
    img = Image.new("RGB", (CW, CH), C_BG)
    return img, ImageDraw.Draw(img, "RGBA")


def paste_map(img, base_path):
    img.paste(Image.open(base_path).convert("RGBA"), (MAP_X, MAP_Y))


def draw_title(d, title_text, subtitle_text):
    d.rectangle([0, 0, 24, 100], fill=C_GREEN)
    d.text((60, 12), title_text, font=font(F_TITLE, 56), fill=C_GREEN)
    d.text((62, 78), subtitle_text, font=font(F_SANS, 22), fill=C_MUTE)


def draw_source(d, source_text):
    d.text((60, 1760), source_text, font=font(F_SANS_I, 18), fill=C_MUTE)


def draw_scalebar(d, extent_w_m, length_m=200):
    m_per_px = extent_w_m / MAP_W
    seg = int(length_m / m_per_px)
    half = seg // 2
    bx, by = MAP_X + 50, MAP_Y + MAP_H - 80
    bh = 14
    d.rectangle([bx, by, bx + half, by + bh], fill=(255, 255, 255, 230), outline=C_INK, width=2)
    d.rectangle([bx + half, by, bx + seg, by + bh], fill=C_INK, outline=C_INK, width=2)
    f = font(F_SANS, 18)
    d.text((bx - 6, by + bh + 4), "0", font=f, fill=C_INK)
    d.text((bx + half - 14, by + bh + 4), f"{length_m // 2}", font=f, fill=C_INK)
    d.text((bx + seg - 22, by + bh + 4), f"{length_m} m", font=f, fill=C_INK)


def draw_north_arrow(d, cx, cy, size=72):
    r = size / 2
    d.polygon(
        [(cx, cy - r), (cx - r * 0.35, cy + r * 0.6), (cx, cy + r * 0.25)],
        fill=(255, 253, 247, 255),
        outline=C_INK,
    )
    d.polygon(
        [(cx, cy - r), (cx + r * 0.35, cy + r * 0.6), (cx, cy + r * 0.25)],
        fill=C_INK,
    )
    d.text((cx, cy - r - 18), "N", font=font(F_SANS_B, 24), fill=C_INK, anchor="mm")


def draw_legend(d, entries, x, y, title, row_h=46, sw=40):
    pad = 20
    tf = font(F_SANS_B, 22)
    lf = font(F_SANS, 22)
    max_w = max(d.textlength(e[0], font=lf) for e in entries)
    pw = int(pad * 2 + sw + 16 + max_w + 20)
    ph = pad * 2 + 40 + row_h * len(entries)
    d.rounded_rectangle(
        [x, y, x + pw, y + ph],
        radius=14,
        fill=(255, 253, 247, 235),
        outline=C_CARDBOR,
        width=2,
    )
    d.text((x + pad, y + pad - 2), title, font=tf, fill=C_GREEN)
    for i, (label, kind, *cols) in enumerate(entries):
        ey = y + pad + 42 + i * row_h
        sx = x + pad
        if kind == "fill":
            fc = cols[0]
            ec = cols[1] if len(cols) > 1 else C_INK
            d.rounded_rectangle([sx, ey, sx + sw, ey + 28], radius=3, fill=fc, outline=ec, width=2)
        elif kind == "line":
            lc = cols[0]
            lw = cols[1] if len(cols) > 1 else 4
            d.line([sx, ey + 14, sx + sw, ey + 14], fill=lc, width=lw)
        d.text((sx + sw + 16, ey - 1), label, font=lf, fill=C_INK)


def compose_map2_slope(base_path, extent_w_m):
    img, d = make_canvas()
    paste_map(img, base_path)
    draw_title(
        d,
        "Slope across Colgate University main campus",
        "Derived from USGS 3DEP 10 m DEM (3 m output), reclassified into three ordinal classes",
    )
    draw_source(
        d,
        "Data: USGS 3DEP 1/3 arc-second DEM. Analysis: A. Bolivar, GEOG 108, 2026. CRS: EPSG:26918 (NAD83 / UTM 18N).",
    )
    draw_scalebar(d, extent_w_m, 200)
    draw_north_arrow(d, MAP_X + MAP_W - 110, MAP_Y + 120)
    draw_legend(
        d,
        [
            ("Flat  (under 5%)", "fill", "#FEE6A0", "#B58F3D"),
            ("Moderate  (5 to 10%)", "fill", "#F3A057", "#7C4A1A"),
            ("Steep  (over 10%)", "fill", "#B83A2B", "#4A0F08"),
        ],
        MAP_X + MAP_W - 460,
        MAP_Y + MAP_H - 290,
        title="Slope class",
    )
    img.save(os.path.join(OUT_DIR, "map2_slope.png"), "PNG", optimize=True)


def compose_map3_coverage(base_path, extent_w_m):
    img, d = make_canvas()
    paste_map(img, base_path)
    draw_title(
        d,
        "Pedestrian path coverage",
        "Campus area within 30 m of a mapped OSM pedestrian path",
    )
    draw_source(
        d,
        "Data: OpenStreetMap (footway, steps, path, pedestrian). Analysis: A. Bolivar, GEOG 108, 2026. CRS: EPSG:26918.",
    )
    draw_scalebar(d, extent_w_m, 200)
    draw_north_arrow(d, MAP_X + MAP_W - 110, MAP_Y + 120)
    draw_legend(
        d,
        [
            ("Within 30 m of a path", "fill", "#B9CDB0", "#5E7E55"),
            ("Beyond 30 m of any path", "fill", "#D4D0C6", "#948F82"),
            ("Pedestrian path (OSM)", "line", "#2A2A2A", 5),
        ],
        MAP_X + MAP_W - 560,
        MAP_Y + MAP_H - 290,
        title="Coverage",
    )
    img.save(os.path.join(OUT_DIR, "map3_coverage.png"), "PNG", optimize=True)


def compose_map4_buildings(base_path, extent_w_m, priority):
    img, d = make_canvas()
    paste_map(img, base_path)
    draw_title(
        d,
        "Buildings by pedestrian accessibility tier",
        "Ninety-seven campus buildings classified by mean slope (25 m buffer) and distance to nearest mapped path",
    )
    draw_source(
        d,
        "Data: OpenStreetMap buildings + paths, USGS 3DEP DEM. Analysis: A. Bolivar, GEOG 108, 2026. CRS: EPSG:26918.",
    )
    draw_scalebar(d, extent_w_m, 200)
    draw_north_arrow(d, MAP_X + MAP_W - 110, MAP_Y + 120)

    for name, _, _, px, py in priority:
        gx, gy = MAP_X + px, MAP_Y + py
        d.ellipse(
            [gx - 42, gy - 42, gx + 42, gy + 42],
            fill=None,
            outline=(176, 58, 46, 110),
            width=6,
        )

    offsets = {1: (-140, 40), 2: (-140, -20), 3: (-120, -20), 4: (120, -40), 5: (90, 40), 6: (120, 40)}
    for i, (name, slope, dist, px, py) in enumerate(priority, 1):
        gx, gy = MAP_X + px, MAP_Y + py
        dx, dy = offsets[i]
        lx, ly = gx + dx, gy + dy
        d.line([gx, gy, lx, ly], fill=(74, 15, 8, 200), width=3)
        br = 24
        d.ellipse([lx - br, ly - br, lx + br, ly + br], fill=C_PRI, outline=(255, 255, 255, 255), width=3)
        d.text((lx, ly), str(i), font=font(F_SANS_B, 26), fill="white", anchor="mm")

    img.save(os.path.join(OUT_DIR, "map4_buildings.png"), "PNG", optimize=True)


def main():
    style_layers()
    boundary = find("Campus Boundary")
    hillshade = find("Hillshade (clipped)")
    slope = find("Slope classes (clipped)")
    paths = find("OSM Paths")
    path_buf = find("Path Coverage (30m buffer)")
    buildings = find("Buildings by accessibility tier")
    esri = find("Esri World Imagery")
    campus_fill = find("Campus fill")

    map_extent, extent_w_m = build_map_extent(boundary)

    base1 = render_layers([boundary, esri], "map1_context_base.png", map_extent)
    base2 = render_layers([boundary, slope, hillshade, campus_fill], "map2_slope_base.png", map_extent)
    base3 = render_layers([boundary, paths, path_buf, campus_fill], "map3_coverage_base.png", map_extent)
    base4 = render_layers([boundary, buildings, paths, hillshade, campus_fill], "map4_buildings_base.png", map_extent)

    compose_map2_slope(base2, extent_w_m)
    compose_map3_coverage(base3, extent_w_m)

    priority = [
        ("Chapel House", 20.0, 120, 1228.7, 902.6),
        ("Drake Hall", 22.2, 51, 1247.0, 778.2),
        ("Base Camp", 15.9, 60, 1035.8, 923.1),
        ("Spear House", 14.7, 50, 1276.4, 601.7),
        ("Foggy Bottom Observatory", 12.0, 83, 1649.0, 688.7),
        ("Frank Dining Hall", 14.5, 38, 1326.2, 723.5),
    ]
    compose_map4_buildings(base4, extent_w_m, priority)


main()
