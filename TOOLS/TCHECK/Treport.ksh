#!/bin/ksh
# Treport.ksh -- the changes in the CFMUTEST baseline built on a
# TACT baseline, by committer: how many files of each type, then -- unless
# -short -- each file's commits, tickets, reviews and diffs.
#
# A standalone translation of Tcheck_tact's list_changes and
# list_detailed_changes (Tcheck_tact -focus changes [-short]), for ksh93
# and zsh as ksh, with the same output: `make test` runs Tcheck_tact's own
# changes tests (test/run_changes_tests.sh) against it.
#
#   Treport.ksh [-no-color] [-tool NAME | -meld] [-batch] [-short] BASELINE
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

# Portable across ksh93 and zsh in ksh emulation -- a /bin/ksh that is zsh:
# no .sh.match (a regex only says whether a line matches; the fields come
# out with ${x#...}, ${x%%...} and set --), no ${s:i:1}.
[ -n "$ZSH_VERSION" ] && emulate ksh

set -o noglob     # tickets, commits and paths are words, never patterns

PROG=${0##*/}
CM_OT=${TCHECK_CM_OT:-/cm/ot}
TACT_ROOT=$CM_OT/TACT
CFMUTEST_ROOT=$CM_OT/CFMUTEST

COLORED=true
BATCH=0
SHORT=0           # -short: the files per committer by type, not each file's changes
DIFF_TOOL=""      # -tool NAME; "" for Emacs ediff links
BASELINE=""

function usage {
    print -r -- "usage: $PROG [-no-color] [-tool NAME | -meld] [-batch] [-short] BASELINE"
    print -r -- "  The changes in the CFMUTEST baseline built on TACT baseline BASELINE"
    print -r -- "  (e.g. 30.0.0.132), by committer and branch."
    print -r -- "  -no-color    Plain output, without ANSI colours (colour is the default)."
    print -r -- "  -c           Coloured output; the default."
    print -r -- "  -tool NAME   Make the diff links open the diff tool NAME -- meld, kompare,"
    print -r -- "               kdiff3, ... (git difftool -t NAME) -- rather than Emacs ediff."
    print -r -- "  -meld        Same as -tool meld."
    print -r -- "  -batch       Emacs ediff links whatever -tool says."
    print -r -- "  -short       Only the files per committer by type, not each file's changes."
    print -r -- "  -h           This help."
    exit 1
}

function die {
    print -r -u2 -- "$PROG: $*"
    exit 1
}

# ---------------------------------------------------------------------------
# Output: cecho/cechon, the original Tcheck_tact.ksh's, defined once the
# options are read (see Main). Colour specs: 'sWr' is bold, white on red
#   s d i u f n h t: bold dim italic underline blink reverse hidden strike
#                    (upper case: the same, off)
#   K R G Y B M C W: foreground black red green yellow blue magenta cyan white
#   k r g y b m c w: background, the same colours
# ---------------------------------------------------------------------------

function hr {
    print -r -- "################################################################################"
}

function trim {                 # TEXT -> REPLY, without surrounding blanks
    typeset s=$1
    while [[ $s == [[:space:]]* ]]; do s=${s#?}; done
    while [[ $s == *[[:space:]] ]]; do s=${s%?}; done
    REPLY=$s
}

# ---------------------------------------------------------------------------
# Reading the report
# ---------------------------------------------------------------------------

function cfmu_baseline_of {     # TACT_NR -> REPLY, the CFMUTEST baseline or ""
    # A CM path for Psort, not a file: /cm/ot whatever TCHECK_CM_OT says.
    # Psort -b lists every build on it: the views built on it first, then
    # the baselines -- the TACT one too.
    typeset answer re='/CFMUTEST/CFMUTEST_CONFIG[!.][^/[:space:]]+$'
    REPLY=""
    print -r -- "/cm/ot/TACT/TACT_CONFIG.$1" | Psort -b 2>/dev/null |
    while read -r answer; do
        if [[ $answer =~ $re ]]; then
            print -r -- "${answer##*/CFMUTEST_CONFIG[.\!]}"
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
    typeset re='review-ok: [[:alnum:]_]+; reviewed-by: [^;]*; review-date: [^;]*;'
    typeset ok by date rest
    REPLY=""
    [[ $1 =~ $re ]] || return
    rest=${1#*review-ok: };     ok=${rest%%;*}
    rest=${rest#*reviewed-by: }; by=${rest%%;*}
    rest=${rest#*review-date: }; date=${rest%%;*}
    trim "$by";   by=$REPLY
    trim "$date"; date=$REPLY
    REPLY="$by on $date"
    [[ $ok == yes ]] || REPLY="$REPLY (review-ok: $ok)"
}

function tickets_of {           # LINE -> REPLY: its RELATED_CHANGES tickets
    typeset re='RELATED_CHANGES="[^"]*"' q='"'
    REPLY=""
    [[ $1 =~ $re ]] || return
    typeset rest=${1#*RELATED_CHANGES=$q}
    set -- ${rest%%$q*}
    REPLY=$*
}

# The section being read: its baselines, the branch merged last, and the
# user branches merged so far with the tickets each merge lists.
S_from="" S_to="" S_branch=""
typeset -a S_names S_tix
typeset -i S_n=0

function new_section {
    S_branch="" S_n=0
    S_names=() S_tix=()
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
    typeset re_diff='^===== Differences between [^[:space:]]+ and [^[:space:]]+'
    typeset re_merge='^Merge from <- [^[:space:]]+ [^[:space:]]+'
    typeset re_change='^(changed|added|removed|deleted)[[:space:]]+[0-9a-f]+:[^[:space:]]+'
    while read -r line; do      # read strips the line's surrounding blanks
        if [[ $line =~ $re_diff ]]; then
            set -- $line        # ===== Differences between A and B
            # "IFPS.CUA_IDL.30.0.0.122" -> 30.0.0.122
            S_from=${4#*.*.} S_to=${6#*.*.}
            new_section
        elif [[ $line == =====* ]]; then
            new_section         # the baselines are the last ones named
        elif [[ $line =~ $re_merge ]]; then
            set -- $line        # Merge from <- SHA SOURCE ...
            sha=$4 source=$5
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
            set -- $line        # VERB SHA:FILE ...
            verb=$1 sha=${2%%:*} file=${2#*:}
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
        cechon Ky "${name%.*}"
        printf '.'
        cecho Wb "${name##*.}"
    else
        cecho Ky "$name"
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
    # stderr closed in the subshell: zsh reports an unmatched pattern itself
    REPLY=$(exec 2>/dev/null; ls -dt "$1"/$2 | head -n 1)
    set -o noglob
}

function echo_ediff {           # A B: the Emacs ediff of two files
    print -r -- "(ediff-files \"$1\" \"$2\")"
}

function echo_emacs {           # FILE: an #emacs: link opening it
    cecho sBw "Look for details in:"
    print -r -- "#emacs:(progn(find-file \"$1\"))"
}

function display_branch_info {  # BRANCH REFERENCE
    typeset who=${1%%.*} name=${1#*.} view ref
    typeset -u WHO=$who NAME=$name
    printf 'FROM BRANCH : '
    cechon Wb "$who"
    printf '.'
    cecho Ky "$name"
    # the view build: the build of TACT_CONFIG.<USER>.<BRANCH>
    newest "$TACT_ROOT/TACT_CONFIG.$WHO.$NAME" "build_*"; view=$REPLY
    if [[ -z $view ]]; then
        print -r -- "NO VIEW BUILD FOUND FOR THIS BRANCH"
    else
        print -r -- "VIEW BUILD DIR: $view"
    fi
    # its test reports, next to the reference baseline's
    newest "$TACT_ROOT/test_reports" "TACT.TACT_CONFIG.$WHO.$NAME-G!31.*"; view=$REPLY
    newest "$TACT_ROOT/test_reports" "$2-G!31.*"; ref=$REPLY
    # the reference baseline's build: the one its test reports are named
    # after -- ...30.0.0.132-G!31.IP.L8-<host>-<date> for build_G!31.IP.L8 --
    # or without reports its newest build_G!31.*
    typeset tag ref_build=""
    if [[ -n $ref ]]; then
        tag=${ref##*/}; tag=${tag#"$2"-}; tag=${tag%%-*}
        ref_build=$TACT_ROOT/${2#TACT.}/build_$tag
    else
        newest "$TACT_ROOT/${2#TACT.}" "build_G!31.*"; ref_build=$REPLY
    fi
    if [[ -n $ref_build && -d $ref_build ]]; then
        print -r -- "REFERENCE BUILD DIR: $ref_build"
    else
        print -r -- "NO REFERENCE BUILD FOUND"
    fi
    if [[ -z $view ]]; then
        print -r -- "NO TEST REPORTS FOUND FOR THIS BRANCH"
    else
        print -r -- "VIEW TEST REPORTS DIR: $view"
        print -r -- "REFERENCE BASELINE DIR: $ref"
        echo_ediff "${ref:+$ref/}general.results.failed-in" "$view/general.results.failed-in"
    fi
}

function changes_report {       # BASELINE -> REPLY: its changes report, or ""
    typeset cfmu                # after a warning saying why there is none
    cfmu_baseline_of "$1"; cfmu=$REPLY
    if [[ -z $cfmu ]]; then
        cecho sWb "WARNING: Psort -b names no CFMUTEST baseline for TACT_CONFIG.$1"
        REPLY=""; return 1
    fi
    REPLY=$CFMUTEST_ROOT/baseline_reports/CFMUTEST.CFMUTEST_CONFIG.$cfmu.changes_report
    if [[ ! -r $REPLY ]]; then
        cecho sWb "WARNING: no changes report for CFMUTEST_CONFIG $cfmu: $REPLY"
        REPLY=""; return 1
    fi
}

function extension_of {         # FILE -> REPLY: after its name's last dot, or ""
    typeset name=${1##*/}
    REPLY=""
    [[ $name == *.* && -n ${name%.*} ]] && REPLY=${name##*.}
}

function files_by_type {        # ENTRY... -> COUNT, its files; REPLY "2 adb, 2 ads"
    # a file changed, added or deleted more than once is one file; the
    # commonest extension first, then by name
    typeset files=" " exts="" by_type="" i f n e tab=$'\t' nl=$'\n'
    COUNT=0
    for i in "$@"; do
        f=${E_file[i]}
        [[ $files == *" $f "* ]] && continue
        files="$files$f " COUNT=$((COUNT + 1))
        extension_of "$f"
        exts=$exts$REPLY$nl
    done
    printf '%s' "$exts" |
    awk '{ n[$0]++ } END { for (e in n) printf "%d\t%s\n", n[e], e }' |
    LC_ALL=C sort -t "$tab" -k1,1nr -k2,2 |
    while IFS=$tab read -r n e; do
        by_type=${by_type:+$by_type, }"$n ${e:-(no extension)}"
    done
    REPLY=$by_type
}

function count_line {           # COUNT WIDTH TYPES: "  4 files: 2 adb, 2 ads"
    typeset noun=files
    (($1 == 1)) && noun="file "
    printf '  %*s %s: %s\n' "$2" "$1" "$noun" "$3"
}

REPORT=""                       # the changes report, once list_changes found it

function list_changes {         # BASELINE: by committer, the most first, their files by type
    typeset who branch entries line
    typeset -i width=0 count_width=0 k
    typeset -a counts types
    hr
    cecho sWr "CHANGES BY COMMITTER"
    changes_report "$1" || return 1
    REPORT=$REPLY
    read_changes "$REPORT"
    for ((k = 0; k < ${#COMMITTERS[@]}; k++)); do
        who=${COMMITTERS[k]}
        entries=""
        for branch in ${BRANCHES[$who]}; do
            entries="$entries ${ENTRIES[$branch]}"
        done
        files_by_type $entries
        counts[k]=$COUNT types[k]=$REPLY
        ((${#who} > width)) && width=${#who}
        ((${#COUNT} > count_width)) && count_width=${#COUNT}
    done
    if [[ -n $UNATTRIBUTED ]]; then
        files_by_type $UNATTRIBUTED
        typeset unattributed_count=$COUNT unattributed_types=$REPLY
        ((${#UNATTRIBUTED_LABEL} > width)) && width=${#UNATTRIBUTED_LABEL}
        ((${#COUNT} > count_width)) && count_width=${#COUNT}
    fi
    # the most files first; as they first appear in the report when as many
    for ((k = 0; k < ${#COMMITTERS[@]}; k++)); do
        print -r -- "${counts[k]} $k"
    done | sort -k1,1nr -k2,2n | while read -r line; do
        k=${line#* }
        who=${COMMITTERS[k]}
        cechon Wb "$who"
        printf '%*s' $((width - ${#who})) ""
        count_line "${counts[k]}" $count_width "${types[k]}"
    done
    if [[ -n $UNATTRIBUTED ]]; then
        printf '%-*s' $width "$UNATTRIBUTED_LABEL"
        count_line "$unattributed_count" $count_width "$unattributed_types"
    fi
    print
}
UNATTRIBUTED_LABEL="(no branch)"

function list_detailed_changes { # BASELINE: each file, its commits, ..., diffs
    typeset reference who branch i report=$REPORT
    hr
    cecho sWr "LIST OF CHANGES"
    # a branch's build is compared with the baseline before this one
    reference=TACT.TACT_CONFIG.${1%.*}.$(( ${1##*.} - 1 ))
    print -r -- "DIFF and NET DIFF run in the file's submodule of the NM workspace, which must be"
    print -r -- "checked out, with the commits and the baseline tags fetched:"
    print -r -- '    git -C $CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY submodule update --init <system>/<subsystem>'
    print -r -- '    git -C $CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY/<system>/<subsystem> fetch --tags'
    print
    for who in "${COMMITTERS[@]}"; do
        printf '%s' "===================================== Files committed by user "
        cechon Wb "$who"
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
    echo_emacs "$report"
    print
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

while (($# > 0)); do
    case $1 in
    -no-color) COLORED=false ;;
    -c)        COLORED=true ;;
    -batch)    BATCH=1 ;;
    -short)    SHORT=1 ;;
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

# some utilities -- the original Tcheck_tact.ksh's, \033 for its \e: echo -e
# and printf '%b' understand \e in zsh, not in ksh93, and \033 in both
if "${COLORED}"; then
  function c { printf "$1" | sed 's/\(.\)/\1;/g;s/\([SDIUFNHT]\)/2\1/g;s/\([KRGYBMCW]\)/3\1/g;s/\([krgybmcw]\)/4\1/g;y/SDIUFNHTsdiufnhtKRGYBMCWkrgybmcw/12345789123457890123456701234567/;s/^\(.*\);$/\\033[\1m/g'; }
  function cecho { echo -e "$(c $1)$2\033[0m"; }
  function cechon { echo -n -e "$(c $1)$2\033[0m"; } # same as cecho but no newline
else
  function cecho  { echo    "$2"; }
  function cechon { echo -n "$2"; }
fi

# the files per committer by type, then -- unless -short -- each file's changes
list_changes "$BASELINE" || exit 1
((SHORT)) || list_detailed_changes "$BASELINE"
