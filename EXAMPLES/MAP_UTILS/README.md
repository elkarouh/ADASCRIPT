# MAP_UTILS -- geospatial geometry, translated

`map_utils.py` is the original: coordinate conversion (DMS <-> decimal degrees),
flat-plane `Vector` / `Position`, and the geodetic `GeoVector` / `GeoPoint` with
the Vincenty direct and inverse formulae, so that `GeoPoint + GeoVector` and
`GeoPoint - GeoPoint` work like their flat-plane counterparts.

`map_utils.ady` is the same module in Adascript (Nim backend: it uses `math`).
What it changes is listed at the top of the file: no bare floats (`Meters_T`,
`Kilometers_T`, `Degrees_T`, `Bearing_T`, distinct `Latitude_T` and `Longitude_T`),
enums where the original had strings and a flag (`Axis_T` for latitude or
longitude, `Hemisphere_T` for the letter a DMS string ends in, `DmsPart_T` for
which field did not parse), a DMS string that does not parse -- or ends in a letter
that is not a side of its axis -- is a failure value, and three things in the
original that did not work are fixed (`normal()`, `projection()`, and the docstring
example of `dms2dec`).

`test_map_utils.ady` checks the translation against numbers printed by the original.
`test_hek_map_utils.py` is the original's pytest file (it imports `hek_map_utils`,
the module's older name here), and `test_hek_map_utils.ady` is its cases in
Adascript, class for class; its header lists the few that do not carry over.
Against `map_utils.py` the pytest file passes 52 of 55: `construct_from_name`
needs the author's `my_aerodromes` module, and two `str()` tests look for the word
"degrees" where `map_utils.py` prints the degree sign (`map_utils.ady` spells it
out, and passes them). It also imports `human2dec_degree`, which `map_utils.py`
does not have; `map_utils.ady` does.
Running `map_utils` prints the original's demo, without its folium map.

`regions.ady` is the Region algebra of `GEO_SERVER/geo_server.ady` -- circles, wedges,
polygons and rings, composed with `&`, `|` and `~` and tested with `in` -- on the
Earth's surface, with `GeoPoint` for a point and the Vincenty distance and bearing for
how far and which way. `test_regions.ady` checks it.

`route_check.ady` is a program that uses the module and the regions: a flight route over
four airports, checked against restricted airspace and an approach funnel built from
regions, with a plane's distance off its track and a holding pattern. It checks its own
results.

`route_map.ady` draws that route on a Folium map -- the route coloured by the airspace it
is in, the zones, the airports, two planes off their track and the holding pattern, each a
layer -- as the original demo drew its points. It needs `pip install folium` for the
Python that nimpy loads, so `make test` only compiles it.

    ady2nim c map_utils.ady && ./map_utils
    ady2nim c -r test_map_utils.ady
    ady2nim c -r test_hek_map_utils.ady
    ady2nim c -r test_regions.ady
    ady2nim c route_check.ady && ./route_check
    ady2nim c route_map.ady && ./route_map [FILE.html [show]]
