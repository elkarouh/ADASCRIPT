#!/bin/ksh
# Treport.ksh -- the changes in the CFMUTEST baseline built on a
# TACT baseline, by committer and branch.
#
# A standalone translation of Tcheck_tact's list_all_changes (Tcheck_tact
# -focus changes), for ksh93, with the same output: `make test` runs
# Tcheck_tact's own changes tests (test/run_changes_tests.sh) against it.
#
#   Treport.ksh [-no-color] [-tool NAME | -meld] [-batch] BASELINE
#
# BASELINE is a TACT baseline number, e.g. 30.0.0.132. `Psort -b` names
# the CFMUTEST baseline built on it, and that baseline's changes report,
#   /cm/ot/CFMUTEST/baseline_reports/CFMUTEST.CFMUTEST_CONFIG.<nr>.changes_report
# lists per component the merges since the previous baseline and the files
# their commits changed, added or removed:
#
#   ===== Differences between TACT.UIF.30.0.0.129 and TACT.UIF.30.0.0.130
#         Merge from <- a2721a86a acicek.transmit_esb RELATED_CHANGES="SC-1 SC-2 "
#         Merge from <- c3fb81031 CFMUTEST.CFMUTEST_CONFIG.30.0.0.104 review-ok: yes; ...
#         changed c3fb81031:TACT/UIF/sources/query_mgr_task.adb RELATED_CHANGES=" " ...
#
# A change is credited to a user branch -- <user>.<branch> -- merged above
# it in its section: the one whose merge lists all the change's SC tickets,
# else the one that shares any, else -- none or several -- the nearest.
# Integration merges (testadm, any ...adm) and baseline syncs
# (CFMUTEST.CFMUTEST_CONFIG.<nr>) are nobody's branch.
#
# Each file's DIFF lines (one per commit) and NET DIFF line (the whole
# baseline's change to it) are #emacs: links: Emacs ediff, or with -tool
# NAME that diff tool through git difftool. They run in the file's
# submodule of $CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY.
#
# Environment: TCHECK_CM_OT, the CM tree (default /cm/ot);
# CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY, the NM workspace.

set -o noglob     # tickets, commits and paths are words, never patterns

PROG=${0##*/}
CM_OT=${TCHECK_CM_OT:-/cm/ot}
TACT_ROOT=$CM_OT/TACT
CFMUTEST_ROOT=$CM_OT/CFMUTEST

COLORED=1
BATCH=0
DIFF_TOOL=""      # -tool NAME; "" for Emacs ediff links
BASELINE=""

function usage {
    print -r -- "usage: $PROG [-no-color] [-tool NAME | -meld] [-batch] BASELINE"
    print -r -- "  The changes in the CFMUTEST baseline built on TACT baseline BASELINE"
    print -r -- "  (e.g. 30.0.0.132), by committer and branch."
    print -r -- "  -no-color    Plain output, without ANSI colours (colour is the default)."
    print -r -- "  -c           Coloured output; the default."
    print -r -- "  -tool NAME   Make the diff links open the diff tool NAME -- meld, kompare,"
    print -r -- "               kdiff3, ... (git difftool -t NAME) -- rather than Emacs ediff."
    print -r -- "  -meld        Same as -tool meld."
    print -r -- "  -batch       Emacs ediff links whatever -tool says."
    print -r -- "  -h           This help."
    exit 1
}

function die {
    print -r -u2 -- "$PROG: $*"
    exit 1
}

# ---------------------------------------------------------------------------
# Output: colour specs as Tcheck_tact's -- 'sWr' is bold, white on red
#   Attr: S/s=bold D/d=dim I/i=italic U/u=underline F/f=blink N/n=reverse
#         H/h=hidden T/t=strike
#   Fg:   K R G Y B M C W (black red green yellow blue magenta cyan white)
#   Bg:   k r g y b m c w
# ---------------------------------------------------------------------------

ESC=$'\033'

function ansi_escape {          # SPEC -> REPLY, the escape sequence or ""
    typeset spec=$1 codes="" c code
    typeset -i i
    for ((i = 0; i < ${#spec}; i++)); do
        c=${spec:i:1}
        case $c in
        S|s) code=1 ;;  D|d) code=2 ;;  I|i) code=3 ;;  U|u) code=4 ;;
        F|f) code=5 ;;  N|n) code=7 ;;  H|h) code=8 ;;  T|t) code=9 ;;
        K) code=30 ;; R) code=31 ;; G) code=32 ;; Y) code=33 ;;
        B) code=34 ;; M) code=35 ;; C) code=36 ;; W) code=37 ;;
        k) code=40 ;; r) code=41 ;; g) code=42 ;; y) code=43 ;;
        b) code=44 ;; m) code=45 ;; c) code=46 ;; w) code=47 ;;
        *) continue ;;
        esac
        codes=${codes:+$codes;}$code
    done
    REPLY=${codes:+$ESC[${codes}m}
}

function puts {                 # SPEC TEXT [nl]: TEXT in colour
    if ((COLORED)); then
        ansi_escape "$1"
        printf '%s%s%s' "$REPLY" "$2" "$ESC[0m"
    else
        printf '%s' "$2"
    fi
    [[ $3 == nl ]] && print
}

function hr {
    print -r -- "################################################################################"
}

function trim {                 # TEXT -> REPLY, without surrounding blanks
    typeset s=$1
    s=${s##+([[:space:]])}
    REPLY=${s%%+([[:space:]])}
}

# ---------------------------------------------------------------------------
# Reading the report
# ---------------------------------------------------------------------------

function cfmu_baseline_of {     # TACT_NR -> REPLY, the CFMUTEST baseline or ""
    # A CM path for Psort, not a file: /cm/ot whatever TCHECK_CM_OT says.
    # Psort -b lists every build on it: the views built on it first, then
    # the baselines -- the TACT one too.
    typeset answer re='/CFMUTEST/CFMUTEST_CONFIG[!.]([^/[:space:]]+)$'
    REPLY=""
    print -r -- "/cm/ot/TACT/TACT_CONFIG.$1" | Psort -b 2>/dev/null |
    while read -r answer; do
        if [[ $answer =~ $re ]]; then
            print -r -- "${.sh.match[1]}"
            break
        fi
    done | read -r REPLY
}

function user_branch {          # NAME -> REPLY: NAME if somebody's branch, else ""
    typeset name=$1 sync='^[A-Z][A-Z0-9_]*\.[A-Z0-9_]+\.[0-9]'
    REPLY=""
    [[ $name =~ $sync ]] && return          # CFMUTEST.CFMUTEST_CONFIG.30.0.0.104
    [[ $name == *.* ]] || return
    [[ ${name%%.*} == *adm ]] && return     # testadm.integration_30
    REPLY=$name
}

function review_of {            # LINE -> REPLY: "dpt, gru on 260922.151702" or ""
    typeset re='review-ok: ([[:alnum:]_]+); reviewed-by: ([^;]*); review-date: ([^;]*);'
    typeset ok by date
    REPLY=""
    [[ $1 =~ $re ]] || return
    ok=${.sh.match[1]} by=${.sh.match[2]} date=${.sh.match[3]}
    trim "$by";   by=$REPLY
    trim "$date"; date=$REPLY
    REPLY="$by on $date"
    [[ $ok == yes ]] || REPLY="$REPLY (review-ok: $ok)"
}

function tickets_of {           # LINE -> REPLY: its RELATED_CHANGES tickets
    typeset re='RELATED_CHANGES="([^"]*)"'
    REPLY=""
    [[ $1 =~ $re ]] || return
    set -- ${.sh.match[1]}
    REPLY=$*
}

# The section being read: its baselines, the branch merged last, and the
# user branches merged so far with the tickets each merge lists.
S_from="" S_to="" S_branch=""
typeset -a S_names S_tix
typeset -i S_n=0

function new_section {
    S_branch="" S_n=0
    unset S_names S_tix
    typeset -a S_names S_tix
}

function credit {               # TICKETS NEAREST -> REPLY, the branch credited
    typeset tickets=$1 covering="" sharing="" t
    typeset -i k all any ncov=0 nshare=0
    REPLY=$2
    [[ -z $tickets ]] && return
    for ((k = 0; k < S_n; k++)); do
        all=1 any=0
        for t in $tickets; do
            if [[ " ${S_tix[k]} " == *" $t "* ]]; then any=1; else all=0; fi
        done
        ((all)) && { ((ncov++)); covering=${S_names[k]}; }
        ((any)) && { ((nshare++)); sharing=${S_names[k]}; }
    done
    if ((ncov == 1)); then REPLY=$covering
    elif ((nshare == 1)); then REPLY=$sharing
    fi
}

# The changes: entry I is E_kind[I] E_file[I] E_commits[I] E_tickets[I]
# (space-separated) E_reviews[I] (newline-separated) E_from[I] E_to[I].
typeset -a E_kind E_file E_commits E_tickets E_reviews E_from E_to
typeset -i N=0
typeset -a COMMITTERS           # in the order each first appears
typeset -A BRANCHES             # committer -> its branches, space-separated
typeset -A ENTRIES              # branch -> its entries, space-separated
typeset -A SEEN                 # "branch|kind|file" -> entry
typeset -A MERGE_REVIEWS        # merge sha -> its review
UNATTRIBUTED=""                 # entries with no branch merged above them

function new_entry {            # KIND FILE -> REPLY, the new entry's index
    E_kind[N]=$1 E_file[N]=$2 E_commits[N]="" E_tickets[N]="" E_reviews[N]=""
    E_from[N]=$S_from E_to[N]=$S_to
    REPLY=$N
    ((N++))
}

function add_to_entry {         # I SHA TICKETS REVIEW
    typeset -i i=$1
    typeset t nl=$'\n'
    [[ " ${E_commits[i]} " == *" $2 "* ]] || E_commits[i]=${E_commits[i]:+${E_commits[i]} }$2
    for t in $3; do
        [[ " ${E_tickets[i]} " == *" $t "* ]] || E_tickets[i]=${E_tickets[i]:+${E_tickets[i]} }$t
    done
    if [[ -n $4 && "$nl${E_reviews[i]}$nl" != *"$nl$4$nl"* ]]; then
        E_reviews[i]=${E_reviews[i]:+${E_reviews[i]}$nl}$4
    fi
}

function read_changes {         # REPORT
    typeset line sha source merged verb kind file tickets review owner who key
    typeset re_diff='^===== Differences between ([^[:space:]]+) and ([^[:space:]]+)'
    typeset re_merge='^Merge from <- ([^[:space:]]+) ([^[:space:]]+)'
    typeset re_change='^(changed|added|removed|deleted)[[:space:]]+([0-9a-f]+):([^[:space:]]+)'
    while read -r line; do      # read strips the line's surrounding blanks
        # Captures are bound first: the functions called match regexes of
        # their own.
        if [[ $line =~ $re_diff ]]; then
            S_from=${.sh.match[1]} S_to=${.sh.match[2]}
            # "IFPS.CUA_IDL.30.0.0.122" -> 30.0.0.122 -- after both are
            # bound: ${x#pattern} resets .sh.match too
            S_from=${S_from#*.*.} S_to=${S_to#*.*.}
            new_section
        elif [[ $line == =====* ]]; then
            new_section         # the baselines are the last ones named
        elif [[ $line =~ $re_merge ]]; then
            sha=${.sh.match[1]} source=${.sh.match[2]}
            review_of "$line"
            [[ -n $REPLY ]] && MERGE_REVIEWS[$sha]=$REPLY
            user_branch "$source"; merged=$REPLY
            if [[ -n $merged ]]; then
                S_branch=$merged
                tickets_of "$line"
                S_names[S_n]=$merged S_tix[S_n]=$REPLY
                ((S_n++))
            elif [[ ${source%%.*} == *adm ]]; then
                S_branch=""     # an integration merge: what follows is nobody's yet
            fi
        elif [[ $line =~ $re_change ]]; then
            verb=${.sh.match[1]} sha=${.sh.match[2]} file=${.sh.match[3]}
            case $verb in
            changed) kind=CHANGED ;;
            added)   kind=ADDED ;;
            *)       kind=DELETED ;;
            esac
            tickets_of "$line"; tickets=$REPLY
            # a merge's review, for the change its own commit makes
            review_of "$line"; review=$REPLY
            [[ -z $review ]] && review=${MERGE_REVIEWS[$sha]}
            credit "$tickets" "$S_branch"; owner=$REPLY
            if [[ -z $owner ]]; then
                new_entry "$kind" "$file"
                add_to_entry "$REPLY" "$sha" "$tickets" "$review"
                UNATTRIBUTED=${UNATTRIBUTED:+$UNATTRIBUTED }$REPLY
                continue
            fi
            who=${owner%%.*}
            if [[ -z ${BRANCHES[$who]+set} ]]; then
                COMMITTERS+=("$who")
                BRANCHES[$who]=""
            fi
            if [[ -z ${ENTRIES[$owner]+set} ]]; then
                BRANCHES[$who]=${BRANCHES[$who]:+${BRANCHES[$who]} }$owner
                ENTRIES[$owner]=""
            fi
            key="$owner|$kind|$file"
            if [[ -z ${SEEN[$key]+set} ]]; then
                new_entry "$kind" "$file"
                SEEN[$key]=$REPLY
                ENTRIES[$owner]=${ENTRIES[$owner]:+${ENTRIES[$owner]} }$REPLY
            fi
            add_to_entry "${SEEN[$key]}" "$sha" "$tickets" "$review"
        fi
    done < "$1"
}

# ---------------------------------------------------------------------------
# The diff links
# ---------------------------------------------------------------------------

function elisp_string {         # TEXT -> REPLY, as an Emacs Lisp string literal
    typeset s=$1 bs='\' q='"'
    s=${s//"$bs"/"$bs$bs"}
    s=${s//"$q"/"$bs$q"}
    REPLY="\"$s\""
}

function split_file {           # FILE -> SUB REST: its submodule, the path in it
    # <system>/<subsystem> is a submodule of the NM workspace; the variable
    # names it when unset -- the shell expands that, and Emacs through
    # substitute-in-file-name.
    typeset root=${CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY:-'$CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY'}
    if [[ $1 == */*/* ]]; then
        typeset system=${1%%/*} rest=${1#*/}
        SUB=$root/$system/${rest%%/*} REST=${rest#*/}
    else
        SUB="" REST=$1
    fi
}

function diff_link {            # FILE REV1 REV2 -> REPLY, the #emacs: link
    typeset file
    split_file "$1"
    if [[ -n $DIFF_TOOL ]]; then
        elisp_string "git ${SUB:+-C $SUB }difftool -y -t $DIFF_TOOL $2 $3 -- $REST"
        REPLY="#emacs:(call-process-shell-command $REPLY nil 0)"
    else
        typeset path=${SUB:+$SUB/}$REST
        elisp_string "$path"; file=$REPLY
        [[ $path == *'$'* ]] && file="(substitute-in-file-name $file)"
        elisp_string "$2"; typeset rev1=$REPLY
        elisp_string "$3"
        REPLY="#emacs:(vc-version-ediff (list $file) $rev1 $REPLY)"
    fi
}

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

function display_file {         # I: FILE <KIND>: <dir>/<base>.<ext>, commits, ...
    typeset -i i=$1
    typeset file=${E_file[i]} parent name c r
    if [[ $file == */* ]]; then parent=${file%/*} name=${file##*/}
    else parent=. name=$file
    fi
    printf 'FILE %s: %s/' "${E_kind[i]}" "$parent"
    if [[ $name == *.* && -n ${name%.*} ]]; then
        puts Ky "${name%.*}"
        printf '.'
        puts Wb "${name##*.}" nl
    else
        puts Ky "$name" nl
    fi
    print -r -- "COMMITS     : ${E_commits[i]}"
    [[ -n ${E_tickets[i]} ]] && print -r -- "TICKETS     : ${E_tickets[i]}"
    if [[ -n ${E_reviews[i]} ]]; then
        print -r -- "${E_reviews[i]}" | while read -r r; do
            print -r -- "REVIEWED BY : $r"
        done
    fi
    for c in ${E_commits[i]}; do
        diff_link "$file" "$c^" "$c"
        print -r -- "DIFF        : $REPLY"
    done
    set -- ${E_commits[i]}
    if (($# > 1)) && [[ -n ${E_from[i]} && -n ${E_to[i]} ]]; then
        diff_link "$file" "${E_from[i]}" "${E_to[i]}"
        print -r -- "NET DIFF    : $REPLY"
    fi
}

function newest {               # DIR PATTERN -> REPLY: newest match, or ""
    set +o noglob
    REPLY=$(ls -dt "$1"/$2 2>/dev/null | head -n 1)
    set -o noglob
}

function display_branch_info {  # BRANCH REFERENCE
    typeset who=${1%%.*} name=${1#*.} view ref
    typeset -u WHO=$who NAME=$name
    printf 'FROM BRANCH : '
    puts Wb "$who"
    printf '.'
    puts Ky "$name" nl
    newest "$TACT_ROOT/test_reports" "TACT.TACT_CONFIG.$WHO.$NAME-G!31.*"; view=$REPLY
    newest "$TACT_ROOT/test_reports" "$2-G!31.*"; ref=$REPLY
    if [[ -z $view ]]; then
        print -r -- "NO VIEW BUILD FOUND FOR THIS BRANCH"
    else
        print -r -- "VIEW BUILD DIR: $view"
        print -r -- "REFERENCE BASELINE DIR: $ref"
        print -r -- "(ediff-files \"${ref:+$ref/}general.results.failed-in\" \"$view/general.results.failed-in\")"
    fi
}

function list_all_changes {     # BASELINE
    typeset cfmu report reference who branch i
    hr
    puts sWr "LIST OF CHANGES" nl
    cfmu_baseline_of "$1"; cfmu=$REPLY
    if [[ -z $cfmu ]]; then
        puts sWb "WARNING: Psort -b names no CFMUTEST baseline for TACT_CONFIG.$1" nl
        return 1
    fi
    report=$CFMUTEST_ROOT/baseline_reports/CFMUTEST.CFMUTEST_CONFIG.$cfmu.changes_report
    if [[ ! -r $report ]]; then
        puts sWb "WARNING: no changes report for CFMUTEST_CONFIG $cfmu: $report" nl
        return 1
    fi
    # a branch's build is compared with the baseline before this one
    reference=TACT.TACT_CONFIG.${1%.*}.$(( ${1##*.} - 1 ))
    read_changes "$report"
    print -r -- "DIFF and NET DIFF run in the file's submodule of the NM workspace, which must be"
    print -r -- "checked out, with the commits and the baseline tags fetched:"
    print -r -- '    git -C $CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY submodule update --init <system>/<subsystem>'
    print -r -- '    git -C $CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY/<system>/<subsystem> fetch --tags'
    print
    for who in "${COMMITTERS[@]}"; do
        printf '%s' "===================================== Files committed by user "
        puts Wb "$who"
        print -r -- " ====================================="
        for branch in ${BRANCHES[$who]}; do
            print -r -- "---------------------------------"
            display_branch_info "$branch" "$reference"
            for i in ${ENTRIES[$branch]}; do
                print -r -- "---------------------------------"
                display_file "$i"
            done
        done
        print
        print
    done
    if [[ -n $UNATTRIBUTED ]]; then
        print -r -- "===================================== Files with no branch merged above them ====================================="
        for i in $UNATTRIBUTED; do
            display_file "$i"
        done
        print
    fi
    print
    puts sBw "Look for details in:" nl
    print -r -- "#emacs:(progn(find-file \"$report\"))"
    print
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

while (($# > 0)); do
    case $1 in
    -no-color) COLORED=0 ;;
    -c)        COLORED=1 ;;
    -batch)    BATCH=1 ;;
    -meld)     DIFF_TOOL=meld ;;
    -tool)
        (($# > 1)) || die "-tool requires the name of a diff tool, e.g. -tool meld"
        shift
        # it goes into a shell command: a tool's name, not a command line
        [[ $1 == +([A-Za-z0-9_.+-]) ]] || die "-tool: not a diff tool's name: $1"
        DIFF_TOOL=$1 ;;
    -h|-help|--help) usage ;;
    -*)        die "unknown option: $1" ;;
    *)         [[ -z $BASELINE ]] || die "one baseline only: $BASELINE and $1"
               BASELINE=$1 ;;
    esac
    shift
done
[[ -n $BASELINE ]] || usage
[[ $BASELINE == +([0-9]).+([0-9.]) ]] || die "not a baseline number: $BASELINE"
((BATCH)) && DIFF_TOOL=""

list_all_changes "$BASELINE"
