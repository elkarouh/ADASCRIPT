# MAP_UTILS -- geospatial geometry, translated

`map_utils.py` is the original: coordinate conversion (DMS <-> decimal degrees),
flat-plane `Vector` / `Position`, and the geodetic `GeoVector` / `GeoPoint` with
the Vincenty direct and inverse formulae, so that `GeoPoint + GeoVector` and
`GeoPoint - GeoPoint` work like their flat-plane counterparts.

`map_utils.ady` is the same module in Adascript (Nim backend: it uses `math`).
What it changes is listed at the top of the file: no bare floats (`Meters_T`,
`Kilometers_T`, `Degrees_T`, `Bearing_T`, distinct `Latitude_T` and `Longitude_T`),
an `Axis_T` enum where the original had `"NS"` / `"EW"` strings and a flag, a
DMS string that does not parse is a failure value, and three things in the
original that did not work are fixed (`normal()`, `projection()`, and the docstring
example of `dms2dec`).

`test_map_utils.ady` checks the translation against numbers printed by the original.
Running `map_utils` prints the original's demo, without its folium map.

    ady2nim c map_utils.ady && ./map_utils
    ady2nim c -r test_map_utils.ady
