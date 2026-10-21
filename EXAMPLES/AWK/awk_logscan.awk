#!/usr/bin/awk -f
#
# awk_logscan.awk -- the same job as awk_logscan.ady, written in awk.
#
# Not a straw man: this is what the program looks like when you have awk's
# tools and only those. Same input, same report, byte for byte:
#
#     awk -f awk_logscan.awk awk_logscan_sample.txt
#     ./awk_logscan < awk_logscan_sample.txt
#
# Written for POSIX awk, so it runs under mawk as well as gawk. What it has
# to spell out by hand, and what that costs, is the subject of
# DOCS/ADASCRIPT_FOR_AWK.md section 10.3.

function status_class(code) {
    # No enum and no case over ranges: an if/else chain, and the names it
    # returns are strings that nothing checks against the ones counted in
    # BEGIN. A typo here is a silently missing row in the report.
    if (code >= 200 && code <= 299) return "SUCCESS"
    if (code >= 300 && code <= 399) return "REDIRECT"
    if (code >= 400 && code <= 499) return "CLIENT_ERROR"
    if (code >= 500 && code <= 599) return "SERVER_ERROR"
    return "ODD"
}

function close_trace() {
    tr_under[ntr] = open_under
    tr_lines[ntr] = open_lines
    tr_failure[ntr] = open_failure
    ntr++
}

function open_trace() {
    open_under = (nreq > 0) ? req_verb[nreq - 1] " " req_path[nreq - 1] : ""
    open_lines = 0
    open_failure = ""
    in_trace = 1
}

BEGIN {
    in_trace = 0
    nreq = 0
    ntr = 0

    # The enums, as strings -- and their declaration order, written out a
    # second time so the report can loop over it. Two lists that have to be
    # kept in step by hand; nothing notices if they drift apart.
    nsev = split("DEBUG INFO WARN ERROR", sev_name, " ")
    for (i = 1; i <= nsev; i++) sev_count[sev_name[i]] = 0

    nstat = split("SUCCESS REDIRECT CLIENT_ERROR SERVER_ERROR ODD", stat_name, " ")
    for (i = 1; i <= nstat; i++) stat_count[stat_name[i]] = 0
}

# --- inside a trace ------------------------------------------------------
# A timestamped line is not part of the trace: close it, leave the state,
# and fall through to the event rules below -- this same record is an event.
in_trace && /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] / {
    close_trace()
    in_trace = 0
}

in_trace {
    open_lines++
    if ($0 ~ /^[A-Za-z_]+(Error|Exception): /) {
        colon = index($0, ":")
        open_failure = substr($0, 1, colon - 1)
    }
    next
}

# --- outside a trace -----------------------------------------------------
# One record, taken apart by position: $1 $2 $3 $4 $5 $6 $7. The names are
# in this comment and nowhere the machine can see them.
NF == 7 && $1 ~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$/ && $7 ~ /^[0-9]+ms$/ {
    # Five parallel arrays with a shared index, because awk has no record.
    req_at[nreq]     = $1 " " $2
    req_verb[nreq]   = $4
    req_path[nreq]   = $5
    req_status[nreq] = $6 + 0
    req_ms[nreq]     = substr($7, 1, length($7) - 2) + 0
    nreq++

    # On the fly: a total needs no second pass.
    sev_count[$3]++
    stat_count[status_class($6 + 0)]++
    next
}

/^Traceback / || /^[A-Za-z_]+(Error|Exception): / {
    # The trace belongs to the request before it -- the last one written
    # into the parallel arrays.
    open_trace()
    open_lines++
    if ($0 ~ /^[A-Za-z_]+(Error|Exception): /) {
        colon = index($0, ":")
        open_failure = substr($0, 1, colon - 1)
    }
    next
}

# Anything else belongs to neither kind, and is ignored.

END {
    # A trace that runs to the end of the file has no following record to
    # close it.
    if (in_trace) close_trace()

    print "--- awk_logscan ---"
    printf "records : %d\n", NR
    printf "requests: %d    traces: %d\n", nreq, ntr

    print ""
    for (i = 1; i <= nsev; i++)
        printf "  %-5s %d\n", sev_name[i], sev_count[sev_name[i]]
    print ""
    for (i = 1; i <= nstat; i++)
        printf "  %-13s %d\n", stat_name[i], stat_count[stat_name[i]]

    # Post-processing. POSIX awk has no sort, so here is one: an insertion
    # sort over a copy of the times, to answer a single median.
    for (i = 0; i < nreq; i++) times[i] = req_ms[i]
    for (i = 1; i < nreq; i++) {
        v = times[i]
        j = i - 1
        while (j >= 0 && times[j] > v) { times[j + 1] = times[j]; j-- }
        times[j + 1] = v
    }

    slow = 0
    slow_i = -1
    for (i = 0; i < nreq; i++)
        if (req_ms[i] > slow) { slow = req_ms[i]; slow_i = i }

    print ""
    if (nreq == 0) {
        # awk would happily print 0 here -- times[] is empty and an unset
        # array element is the empty string, which is 0 in a %d. That is
        # the wrong answer rather than no answer, so say so.
        print "p50     : n/a"
        print "slowest : n/a"
    } else {
        printf "p50     : %d ms\n", times[int(nreq / 2)]
        printf "slowest : %d ms  %s %s at %s\n", \
               req_ms[slow_i], req_verb[slow_i], req_path[slow_i], req_at[slow_i]
    }

    print ""
    for (i = 0; i < ntr; i++)
        printf "  trace   %d line(s) under %s -- %s\n", \
               tr_lines[i], tr_under[i], tr_failure[i]
}
