# OPLOG: the TACT ARCHIVED_OPLOG decoder

- `decode_oplog.ady` decodes the log: the header of every record and, for the CPM/CPF
  messages, the position reports (ASTERIX category 62, TACT's variant, and 21).
- `decode_oplog_awk.ady` is the same program on the stdlib's `AwkProcessor` (a record is
  what ends in CR LF); the Makefile checks that the two print the same.
- `sample_oplog.txt` is a log to try them on.

```
decode_oplog sample_oplog.txt                       # everything
decode_oplog day1.txt day2.txt                      # several files: their records in time order
decode_oplog sample_oplog.txt --callsign TAM8149    # the records and reports of one flight
decode_oplog sample_oplog.txt --callsign TAM8149 --html flight.html
```

A report is of the callsign when it names it, itself or in its flight plan, or when it is of an
aircraft (by its Mode-S address) that was seen naming it. A record is also kept when its subject
or its IFPS id is the callsign.

`--html` writes a page with the flight's track on a Leaflet map and the entries of the log
about it in a list beside it; clicking an entry zooms to the reports it holds. The page's
script is `oplog_map.ady`, a browser script (`ady2nim js`) that reads the data from the page
and draws it with the stdlib's `browser` and `leaflet_utils`. `make page CALLSIGN=...` builds
both and writes `flight.html`; `make run` serves it. It loads Leaflet and the map tiles from
the internet, and the tile server refuses a page opened straight from the disk (it wants a
referrer), so serve it with `make run` rather than opening `flight.html`.
