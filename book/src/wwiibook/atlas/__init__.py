"""The atlas: one operational geography drawn twice, from one extent file (atlas/<name>/extent.yml).

  sources      IGN SCAN 50 1950 tiles and its sheet index (editions), Copernicus GLO-30, the Geofabrik OSM extract:
               fetched once into the cache, never edited.
  reconstruct  the period roads and railways (and rivers, places, junctions, crossings) as attributed vectors, each
               feature with its source, source date, historical validity, confidence and a verification note:
               atlas/<name>/infrastructure/*.geojson, versioned, separate from any rendering.
  panorama     the situation, top-down: front, divisions, the network, a locator.
  oblique      the ground, in perspective, the same extent and the same marks.
  qgis         a GeoPackage of the same layers and the terrain, for QGIS 3D.
"""
