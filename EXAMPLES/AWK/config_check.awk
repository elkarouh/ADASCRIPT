#!/usr/bin/awk -f
#
# config_check.awk -- the same job as config_check.ady, in awk.
#
#     awk -f config_check.awk /tmp/ady_config_check/app.conf
#
# Same schema, same findings, same report, byte for byte. Written for POSIX
# awk, so mawk runs it too.
#
# The subject of DOCS/ADASCRIPT_FOR_AWK.md section 10.2 is the schema, and
# this is what a schema looks like without a variant record: one flat set of
# arrays in which every setting has every field. `lo` and `hi` exist for the
# CHOICE settings too -- empty, meaningless, and readable. Nothing stops
# check_value() from consulting spec_lo["mode"]; it would simply compare
# against "" and report that 5 is outside 0 .. 0. The Adascript version
# cannot be written that way: in the CHOICE branch the field is not there.

function spec(key, kind, a, b, c) {
    # One constructor for four shapes, so it takes the union of their
    # fields and each call leaves most of them empty. Which of a, b, c
    # means what depends on `kind`, and only the comments say so.
    spec_kind[key] = kind
    keys[nkeys++] = key
    if (kind == "FLAG")     spec_default[key] = a          # on_by_default
    if (kind == "NUMBER")   { spec_lo[key] = a; spec_hi[key] = b }
    if (kind == "CHOICE")   spec_allowed[key] = a          # a blank-separated list
    if (kind == "PATHNAME") spec_must_exist[key] = a
}

function describe(key,   k) {
    k = spec_kind[key]
    if (k == "FLAG")     return "a flag (" commas(TRUE_LIST) " / " commas(FALSE_LIST) ")"
    if (k == "NUMBER")   return "a whole number in " spec_lo[key] " .. " spec_hi[key]
    if (k == "CHOICE")   return "one of " commas(spec_allowed[key])
    if (k == "PATHNAME") return spec_must_exist[key] ? "a path that must exist" : "a path"
    return "???"   # no enum, so no compiler to say this cannot happen
}

function commas(list,   n, w, i, out) {
    n = split(list, w, " ")
    out = ""
    for (i = 1; i <= n; i++) out = out (i > 1 ? ", " : "") w[i]
    return out
}

function in_list(word, list,   n, w, i) {
    n = split(list, w, " ")
    for (i = 1; i <= n; i++) if (w[i] == word) return 1
    return 0
}

function is_dir(path,   rc) {
    # awk cannot ask about a path, so it asks the shell -- a process per
    # check, and the quoting is the caller's problem.
    rc = system("test -d '" path "'")
    return rc == 0
}

function check_value(key, value,   k, n) {
    k = spec_kind[key]
    if (k == "FLAG") {
        if (in_list(tolower(value), TRUE_LIST) || in_list(tolower(value), FALSE_LIST))
            return ""
        return "'" value "' is not a yes/no word"
    }
    if (k == "NUMBER") {
        if (value !~ /^-?[0-9]+$/) return "'" value "' is not a whole number"
        n = value + 0
        if (n < spec_lo[key] || n > spec_hi[key])
            return n " is outside " spec_lo[key] " .. " spec_hi[key]
        return ""
    }
    if (k == "CHOICE") {
        if (in_list(value, spec_allowed[key])) return ""
        return "'" value "' is not one of " commas(spec_allowed[key])
    }
    if (k == "PATHNAME") {
        if (spec_must_exist[key] && !is_dir(value))
            return "'" value "' is not an existing directory"
        return ""
    }
    return ""
}

function finding(line, level, key, text) {
    # Four parallel arrays and an index, because awk has no record -- and
    # "no line" has to be encoded as the empty string, which is also what a
    # missing array element is, so the two are indistinguishable.
    f_line[nf] = line
    f_level[nf] = level
    f_key[nf] = key
    f_text[nf] = text
    nf++
}

BEGIN {
    TRUE_LIST  = "true yes on 1"
    FALSE_LIST = "false no off 0"

    nkeys = 0
    spec("verbose",   "FLAG",     0)
    spec("workers",   "NUMBER",   1, 64)
    spec("mode",      "CHOICE",   "fast safe paranoid")
    spec("log_dir",   "PATHNAME", 1)
    spec("cache_dir", "PATHNAME", 0)

    REQUIRED = "workers mode log_dir"

    nf = 0
    nlevel = split("NOTE WARNING ERROR", level_name, " ")
    for (i = 1; i <= nlevel; i++) level_count[level_name[i]] = 0
}

{
    line = $0
    sub(/^[ \t]+/, "", line)
    sub(/[ \t]+$/, "", line)

    if (line == "" || line ~ /^[#;]/) next

    if (line !~ /^[A-Za-z0-9_]+[ \t]*=/) {
        finding(NR, "ERROR", "", "not a 'key = value' line")
        next
    }

    eq = index(line, "=")
    key = substr(line, 1, eq - 1)
    value = substr(line, eq + 1)
    sub(/[ \t]+$/, "", key)
    sub(/^[ \t]+/, "", value)
    sub(/[ \t]+$/, "", value)

    if (!(key in spec_kind)) {
        finding(NR, "ERROR", key, "unknown setting")
        next
    }

    if (key in seen)
        finding(NR, "WARNING", key, "set more than once; the last one wins")
    seen[key] = 1

    complaint = check_value(key, value)
    if (complaint != "")
        finding(NR, "ERROR", key, complaint " -- expected " describe(key))
}

END {
    n = split(REQUIRED, req, " ")
    for (i = 1; i <= n; i++)
        if (!(req[i] in seen))
            finding("", "ERROR", req[i],
                    "required setting is missing -- expected " describe(req[i]))

    for (i = 0; i < nkeys; i++)
        if (!(keys[i] in seen) && !in_list(keys[i], REQUIRED))
            finding("", "NOTE", keys[i], "not set; " describe(keys[i]))

    printf "--- config_check %s ---\n", FILENAME
    for (i = 0; i < nf; i++) {
        level_count[f_level[i]]++
        where = (f_line[i] == "") ? "" : "line " f_line[i]
        printf "  %-7s %-8s %-10s %s\n", f_level[i], where, f_key[i], f_text[i]
    }

    print ""
    for (i = 1; i <= nlevel; i++)
        printf "  %-7s %d\n", level_name[i], level_count[level_name[i]]

    exit (level_count["ERROR"] > 0) ? 1 : 0
}
