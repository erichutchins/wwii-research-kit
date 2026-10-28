# /// script
# requires-python = ">=3.9"
# dependencies = ["pillow"]
# ///
"""Shaded relief and a land mask for a map view, from the AWS Terrain Tiles (SOURCES.yml aws-terrain-tiles).

The pages' maps are Web Mercator, so the tiles line up with them directly. For a box this writes, under
records/relief/<name>/:
  land.png     white where the ground is above sea level, transparent elsewhere: a page fills it with its own
               land colour (so it works in light and dark mode). Its coastline is today's, at the tiles'
               resolution (tens of metres): harbour works and reclaimed land built since the war show as land.
  shade.png    hillshade (sun from the north-west, 45 degrees up) as black (shadow) and white (lit) with alpha,
               drawn over the land fill; flat ground stays clear.
  relief.json  the box ([west, south], [east, north]) in degrees, the zoom, and the source.

  uv run tools/build_relief.py algiers 2.72 36.60 3.42 37.08 --zoom 12
  uv run tools/build_relief.py algiers-town 2.94 36.70 3.13 36.83 --zoom 14   (a page draws the finer one on top)
"""
import argparse
import io
import json
import math
import urllib.request
from pathlib import Path

from PIL import Image, ImageFilter

from records import RECORDS

TILES = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"


def tile_xy(lon, lat, z):
    n = 2 ** z
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return (lon + 180) / 360 * n, y


def lonlat(x, y, z):
    n = 2 ** z
    return x / n * 360 - 180, math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))


def fetch(z, x, y, cache):
    f = cache / f"{z}-{x}-{y}.png"
    if not f.exists():
        req = urllib.request.Request(TILES.format(z=z, x=x, y=y), headers={"User-Agent": "wwii-research-kit"})
        f.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    return Image.open(io.BytesIO(f.read_bytes())).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("box", nargs=4, type=float, help="west south east north")
    ap.add_argument("--zoom", type=int, default=12)
    a = ap.parse_args()
    w, s, e, n = a.box
    z = a.zoom
    x0, y0 = tile_xy(w, n, z)
    x1, y1 = tile_xy(e, s, z)
    tx0, ty0, tx1, ty1 = int(x0), int(y0), int(x1), int(y1)
    cache = RECORDS.parent / "sources" / "terrain-tiles"
    cache.mkdir(parents=True, exist_ok=True)
    W, H = (tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256
    mosaic = Image.new("RGB", (W, H))
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            mosaic.paste(fetch(z, tx, ty, cache), ((tx - tx0) * 256, (ty - ty0) * 256))
    # crop to the box
    cx0, cy0 = int((x0 - tx0) * 256), int((y0 - ty0) * 256)
    cx1, cy1 = int((x1 - tx0) * 256), int((y1 - ty0) * 256)
    mosaic = mosaic.crop((cx0, cy0, cx1, cy1))
    W, H = mosaic.size
    px = mosaic.load()
    elev = [[px[i, j][0] * 256 + px[i, j][1] + px[i, j][2] / 256 - 32768 for i in range(W)] for j in range(H)]
    # metres per pixel at the box's middle latitude
    mpp = 40075016.686 * math.cos(math.radians((s + n) / 2)) / (256 * 2 ** z)
    land = Image.new("LA", (W, H))
    shade = Image.new("LA", (W, H))
    lp, sp = land.load(), shade.load()
    az, alt = math.radians(315), math.radians(45)
    for j in range(H):
        for i in range(W):
            e0 = elev[j][i]
            if e0 <= 0:
                lp[i, j] = (255, 0)
                sp[i, j] = (0, 0)
                continue
            lp[i, j] = (255, 255)
            dzdx = (elev[j][min(i + 1, W - 1)] - elev[j][max(i - 1, 0)]) / (2 * mpp)
            dzdy = (elev[min(j + 1, H - 1)][i] - elev[max(j - 1, 0)][i]) / (2 * mpp)
            slope = math.atan(1.5 * math.hypot(dzdx, dzdy))   # 1.5x vertical exaggeration
            aspect = math.atan2(dzdy, -dzdx)
            hs = math.sin(alt) * math.cos(slope) + math.cos(alt) * math.sin(slope) * math.cos(az - aspect)
            flat = math.sin(alt)
            d = hs - flat   # negative: in shadow; positive: lit
            sp[i, j] = (0, min(150, int(-d * 260))) if d < 0 else (255, min(90, int(d * 200)))
    # the coast: sea-level noise in the tiles speckles the shore at large zooms, so the mask is smoothed (a median
    # over 5 px, then a blur) and the hillshade kept only where the smoothed mask says land
    # blur and re-threshold: rounds off the blocks of the coarser source data under the larger zooms
    r = max(2, 2 ** (z - 12))
    land = land.getchannel("A").filter(ImageFilter.MedianFilter(5)).filter(ImageFilter.GaussianBlur(r * 1.5)).point(lambda v: 255 if v >= 128 else 0)
    shade.putalpha(Image.composite(shade.getchannel("A"), Image.new("L", (W, H), 0), land))
    land = Image.merge("LA", (Image.new("L", (W, H), 255), land))
    out = RECORDS / "relief" / a.name
    out.mkdir(parents=True, exist_ok=True)
    land.save(out / "land.png", optimize=True)
    shade.save(out / "shade.png", optimize=True)
    bw, bn = lonlat(tx0 + cx0 / 256, ty0 + cy0 / 256, z)
    be, bs = lonlat(tx0 + cx1 / 256, ty0 + cy1 / 256, z)
    (out / "relief.json").write_text(json.dumps({
        "box": [[round(bw, 6), round(bs, 6)], [round(be, 6), round(bn, 6)]], "zoom": z, "size": [W, H],
        "source": "aws-terrain-tiles", "note": "Today's coastline at the tiles' resolution; harbour works since 1943 show as land."}, indent=1) + "\n")
    print(f"wrote {out}: {W}x{H} px, zoom {z}, {mpp:.0f} m/px")


if __name__ == "__main__":
    main()
