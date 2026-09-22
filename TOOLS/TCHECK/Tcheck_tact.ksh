#!/usr/bin/env ksh
# Todo: replace the python one-liner

# Usage function to display help message
function usage {
  cat <<- "EOF"
    This script will report the status of a baseline build,
    scan the size of replay_dirs of all baselines of the same branch.
    See how_to_tactdev for tips for buildmaster.
EOF
  echo "    usage: $(basename $0) [-c] [-s] [-h] [-v] [-f] [<BASELINE>]"
  echo "    Example: $(basename $0) -c 28.2.0.430"
  echo 'Options:'
  echo '  -c           Show the coloured version.'
  echo '  -s           Compute the sizes ot replay dirs (no parameter expected for -s).'
  echo '  -h           Display this help message and exit.'
  echo '  -f           Fast mode: skip run check_run_test_programs_log.'
  echo '               This may be useful for baseline still running for which this program has not yet been run in the baseline'
  echo '               (in which case the check_run_test_programs_log is launched here.'
  echo '  -v           Enable the VERBOSE option (more info).'
  echo '  <BASELINE>        Required if -c or -v is specified, or if no options are given.'
  exit 1
}

# Initialize flags
COLORED=false
COMPUTE_SIZE=false
VERBOSE=false

if [[ -z "${CONTEXT_CM_BASELINE}" ]]; then
  echo 'Please use this script in an emacs shell within a context'
  usage
fi

# Parse options using getopts
while getopts ":cshvf" opt; do
  case ${opt} in
    c)
      COLORED=true
      ;;
    s)
      COMPUTE_SIZE=true
      ;;
    h)
      usage  # Display help and exit
      ;;
    v)
      VERBOSE=true
      ;;
    f)
      FAST_MODE=true
      ;;
    \?)
      echo "Invalid option: -${OPTARG}" >&2
      usage
      ;;
  esac
done
shift $(( OPTIND - 1 ))

if "${COLORED}" || "${VERBOSE}" || ! "${COMPUTE_SIZE}"; then
  if (( $# == 0 )); then
    echo "Error: <BASELINE> is required when -c or -v is specified, or when no options are given." >&2
    usage
  else
    baseline_to_check="$1"
  fi
fi

###################################################################################
# some utilities
if "${COLORED}"; then
  function c { printf "$1" | sed 's/\(.\)/\1;/g;s/\([SDIUFNHT]\)/2\1/g;s/\([KRGYBMCW]\)/3\1/g;s/\([krgybmcw]\)/4\1/g;y/SDIUFNHTsdiufnhtKRGYBMCWkrgybmcw/12345789123457890123456701234567/;s/^\(.*\);$/\\e[\1m/g'; }
  function cecho { echo -e "$(c $1)$2\e[0m"; }
  function cechon { echo -n -e "$(c $1)$2\e[0m"; } # same as cecho but no newline
else
  function cecho  { echo    "$2"; }
  function cechon { echo -n "$2"; }
fi

function write2prompt {
  # Writes the input to the shell such that the user can type enter to use the command or first edit it if needed.
  perl -e 'ioctl STDOUT, 0x5412, $_ for split //, do{ chomp($_ = <>); $_ }' ;
}

function echo_emacs {
  cecho sBw "Look for details in:"
  printf '#emacs:(progn(find-file "%s"))\n' "$1"
}

function echo_ediff {
  printf '(ediff-files "%s" "%s")\n' "$1" "$2"
}

function hr {
  typeset -r word="${1:-#}"
  typeset -r length="${2:-80}"
  typeset -r blanks=$(printf "%${length}s" '')
  printf '%s\n' "${blanks// /${word}}"
}

function show_available_builds {
  ls -ld build_G!*
}

function process_file {
  typeset -r filename=$1
  typeset -r build_subtype=$2
  unset AT_LEAST_ONE_FAILING_TEST
  # echo "Processing file ${filename}"
  typeset -r -a patterns=(
    'Crashed Tests'
    # "I've executed tests not asked"
    # 'mrun failing'  # The MRUN Tlog is parsed separately.
    # 'Check build of TACT.TACT_CONFIG.'  # ?? Will be removed.
    'New tests failing'
    'Tests that did not run'
    'Tests still failing'
    'Following tests are now successful'
    # 'All executed tests'  # Only written to TLOG_TRACE_LOG.
    # 'All results'
    'Following tests contain known failures'
    # 'Following tests contain known assert failures'
    # 'Tests that are removed'
    'Errors in log files'
    # 'Check build of TACT.TACT_CONFIG.'  # ?? Will be removed.
    'Tlog summary'
  )
  # Find patterns and their line numbers.
  # See function section_print_title in Tlog.ksh to know all section titles to handle here.

  # To add a new section: add a pattern to detect the beginning of the record. Then add the pattern also to the if statement inside the for loop below.
  # Moreover, you probably also need an if statement to print the line inside the aforementioned if statement.

  typeset -A patterns_with_line_number
  for pattern in "${patterns[@]}"; do
    line_number=$(grep -n -m 1 "${pattern}" "${filename}" | cut -d ":" -f 1)
    if [[ -n ${line_number} ]]; then
      patterns_with_line_number[${line_number}]=${pattern}
    fi
  done

  # Sort line numbers
  typeset -r -a sorted_line_numbers=($(printf '%s\n' "${!patterns_with_line_number[@]}" | sort -n))
  typeset -r -i last_sorted_index=$(( ${#sorted_line_numbers[@]} - 2 ))

  # Print pairs of line numbers with current pattern
  for i in $(seq 0 ${last_sorted_index}); do
    typeset current_line="${sorted_line_numbers[${i}]}"

    typeset next_line="${sorted_line_numbers[${i}+1]}"

    typeset current_pattern="${patterns_with_line_number[${current_line}]}"

    for pattern in "${patterns[0]}"  "${patterns[1]}" "${patterns[2]}" "${patterns[3]}" "${patterns[4]}"; do
      if [[ "${current_pattern}" == "${pattern}" ]]; then
        lines=$(sed -n "$((current_line+1)),$((next_line-1))p" "${filename}")
        number_of_lines=$(grep -v -e '^[[:space:]]*$' <<< "${lines}" |  grep -c '^')
        if (( number_of_lines != 0 )); then
          if [[ "${current_pattern}" != "${patterns[2]}" || ${build_subtype} != mono ]]; then
            AT_LEAST_ONE_FAILING_TEST=True
            cecho Kw "${current_pattern}"
          fi
          grep -v -e '^[[:space:]]*$' <<< "${lines}" |
            while read -r line; do
              if [[ "${current_pattern}" == "${patterns[2]}" ]]; then
                if [[ ${build_subtype} != mono ]]; then
                  printf '%s\n' "${line}"  # tests that did not run are written in full except for mono
                fi
              elif [[ "${current_pattern}" == "${patterns[0]}" ]]; then  # CRASHED TESTS
                echo "CRASHED TEST: ${line}"
              elif [[ "${current_pattern}" == "${patterns[4]}" ]]; then  # Errors in logs
                printf '%s\n' "${line}"
              elif [[ "${line}" == *Worse* || "${line}" == *Better* || "${line}" == *Same* ]]; then
                # NOTE: The notation 'Better : 1' etc. in the still failing section is a recent addition.
                # Hopefully the syntax will stay the same but in case it changes this check might need a modification.
                # If this pattern does not work, it will cause mangled output (I saw a single colon being printed).
                echo "${line}"
              else
                failed_test=$(cut -d ' ' -f 2 <<< "${line}")
                printf '\t'
                emacs_command=$(grep -o '#emacs.*' <<< "${line}")
                cecho sKy "${failed_test}"
                echo "${emacs_command}"
              fi
              echo
            done
        else
          cechon Kw "${current_pattern}"
          echo '  ==> None'
          echo
        fi
        break
      fi
    done
  done

  if [[ -z ${AT_LEAST_ONE_FAILING_TEST} ]]; then
    echo
    cecho Kw ".............. ALL TESTS ARE SUCCESSFUL !!!!"
  fi
}  # process_file
####################################################################
function display_file_changed_or_added_or_deleted {
  typeset -r filepath=$1
  typeset -r the_change=$2
  typeset -r path=$(dirname "${filepath}")
  typeset base=$(basename "${filepath}")
  typeset -r extension="${base##*.}"
  base="${base%.*}"
  echo -n "FILE ${the_change}: ${path}/"
  cechon Ky "${base}"
  echo -n .
  cecho Wb "${extension}"
}

function display_view_info {
  typeset -r view=$1
  typeset -r part1=$(echo "${view}" | rev | cut -d'.' -f3- | rev)
  typeset -r committer=$(echo "${view}" | rev | cut -d'.' -f2 | rev)
  typeset -r rest=$(echo "${view}" | rev | cut -d'.' -f1 | rev)
  typeset -r viewshort=$(echo "${view}" | rev | cut -d'.' -f1 | cut -d'/' -f2 | rev)
  typeset -r reference_baseline=$(echo "${part1}" | cut -d'.' -f1-6)
  echo -n "FROM VIEW   : ${part1}."
  cechon Wb "${committer}"
  echo -n .
  cecho Ky "${rest}"
  typeset -r VIEW_BUILD_DIR=$(ls -dt /cm/ot/TACT/test_reports/TACT.TACT_CONFIG.${committer:u}.${viewshort:u}-G!31.* 2>/dev/null | head -n 1)
  typeset -r REF_BUILD_DIR=$(ls -dt /cm/ot/TACT/test_reports/${reference_baseline}-G!31.* 2>/dev/null | head -n 1)
  #??>>eliitiai Hardcoded G!31 is not good.

  if [[ -z "${VIEW_BUILD_DIR}" ]]; then
    echo "NO VIEW BUILD FOUND FOR THIS VIEW"
  else
    echo "VIEW BUILD DIR: ${VIEW_BUILD_DIR}"
    echo "REFERENCE BASELINE DIR: ${REF_BUILD_DIR}"
    echo_ediff "${REF_BUILD_DIR}/general.results.failed-in" "${VIEW_BUILD_DIR}/general.results.failed-in"
  fi
}

function list_all_changes {
  hr
  typeset -A committer_2_files_changed
  cecho sWr "LIST OF CHANGES"
  CHANGES=/cm/ot/TACT/baseline_reports/TACT.TACT_CONFIG.${FULL_BASELINE}.changes_report
  change_detected=false
  CURRENT_FILE=""
  CURRENT_DIFF_CMD=""
  the_change=""
  while IFS= read -r line; do
    stripped_line=${line#"${line%%[![:space:]]*}"}
    if [[ "${stripped_line}" == changed* && ${line} == *"ediff"* ]]; then
      sep="#emacs:"
      diff_cmd="${sep}${line##*"${sep}"}"
      CURRENT_DIFF_CMD="DIFF        :${diff_cmd//$'\n'/ }"
      ####
      filepath=$(echo "${diff_cmd}" | tr -s ' ' | cut -d ' ' -f3 | tr -d "'" | tr -d '"' | cut -d '@' -f1)
      CURRENT_FILE=${filepath}
      the_change=CHANGED
      change_detected=true
    elif [[ "${stripped_line}" == added* ]]; then
      CURRENT_FILE=$(echo ${stripped_line} | cut -d' ' -f2-)
      the_change=ADDED
      change_detected=true
    elif [[ "${stripped_line}" == deleted* ]]; then
      CURRENT_FILE=$(echo ${stripped_line} | cut -d' ' -f2-)
      the_change=DELETED
      change_detected=true
    elif [[ "${stripped_line}" == "<- Merged from branch:"* ]] &&
           [[ "${line}" != *"ifpsadm"* ]] &&
           [[ "${line}" != *"eldadm"* ]] &&
           [[ "${line}" != *"tactadm"* ]] &&
           [[ "${line}" != *"TOOL.COMMON"* ]] &&
           ${change_detected}; then
      view=${line##*/main/}
      committer=$(echo "${view}" | rev | cut -d'.' -f2 | rev)
      record="${the_change}|${CURRENT_FILE}|${CURRENT_DIFF_CMD}|${view}%%%%"
      record=$(sed 's/ /====/g' <<< "${record}") # Mangle to avoid whitespace nightmare.
      committer_2_files_changed[${committer}]+=${record}
      change_detected=false
    fi
  done < "${CHANGES}"
  for committer in "${!committer_2_files_changed[@]}"; do
    echo -n "===================================== Files committed by user "
    cechon Wb "${committer}"
    echo   " ====================================="
    fields="${committer_2_files_changed[${committer}]}"
    # Iterate over the fields
    OLD_IFS="${IFS}"
    IFS="%%%%"
    for record in ${fields}; do
      IFS="|"
      if [[ -z ${record} ]]; then continue;fi
      i=0
      echo ---------------------------------
      for field in ${record}; do
        field="${field//====/ }" # undo the mangling
        case ${i} in
          0)
            the_change=${field}
            ;;
          1)
            CURRENT_FILE=${field}
            display_file_changed_or_added_or_deleted ${CURRENT_FILE} ${the_change}
            ;;
          2) CURRENT_DIFF_CMD=${field}
             if [[ ${the_change} == CHANGED ]];then
               echo ${CURRENT_DIFF_CMD}
             fi
             ;;
          3) view=${field}
             display_view_info ${view}
             ;;
        esac
        (( ++i ))
      done
      IFS="${OLD_IFS}"
    done
    echo
    echo
  done
  echo
  echo_emacs "${CHANGES}"
  echo
}  # list_all_changes

function process_builds {
  hr
  cecho sWr "TESTS"
  for build in $1; do
    if ! echo "${build}" | grep -qE '92|94|95|98|30'; then # skip these builds.
      process_build ${build}
    fi
  done
}

function grep_force_trace_in_dir {
  typeset -r dir=$1

  if [[ ! -d "${dir}" ]]; then
    cecho sWb "WARNING: '${dir}' does not exist!"
    return 1
  fi

  # Consider the following code:
  # #
  # Debug.Trace (Trc, "str1" + "str2")
  #
  # without "if Debug.Trace (Trc)". The dynamic string concatenation would be done in all cases, which is not wanted.
  # Therefore in LO build, when FORCE_TRACE debug flag is set, a check is made to ensure that the debug message is not dynamic.
  # The result error message in the logs is
  # !!! ERROR : FORCE_TRACE message above is treated as Assertion Error. : (FORCE_TRACE) !!! <25/01/09-09:47:06.97>
  # The see the debug trace causing the problem we should look at the previous line.

  cecho sWb "Grep in ${dir} to detect missing 'if Debug.Trace (...) then' (100 first errors, no matches means no errors detected):"

  typeset -r pattern='!!! ERROR : FORCE_TRACE message above'

  for f in "${dir}"/*_out_*; do
    # The pattern gets expanded only if there is a matching file in the directory.
    if [[ -e "${f}" ]]; then
      grep -H -n -B1 "${pattern}" "${f}" |grep -v '^--\s*$'
    fi
  done |head -n 100
}  # grep_force_trace_in_dir

function lo_build_checks {
  typeset -r tacot_corico_latest=$1

  typeset -r lo_logdir="${tacot_corico_latest}/work/logging-lo"

  if [[ -e "${lo_logdir}" ]]; then
    cecho syB "Doing lo-build checks in ${lo_logdir}"
    typeset -r log_dir="${lo_logdir}/LOGS"
    typeset -r log_others_dir="${lo_logdir}/LOGS_others"

    grep_force_trace_in_dir "${log_dir}"
    grep_force_trace_in_dir "${log_others_dir}"
  fi
}

function show_tlog_if_present {
  typeset -r build_name=$1
  typeset -r build_subtype=$2
  typeset -r tacot_corico_dir=$3
  typeset -r file=$4

  typeset -r full_path="${tacot_corico_dir}/TACT_REGRESS_LOGS/LATEST/${file}"

  typeset -r mandatory='(IP|OP)'
  typeset -r build_type=$(echo "${build_name}" | awk -F'.' '{ print $(NF-1) }') # Extract middle of CM_ENV_ID, IP, OP, SIP...

  if [[ -f ${full_path} ]]; then

    echo -n "=======================================  "
    cechon sWr $(basename "${full_path}")
    echo -n " "
    cechon sWb " (${build_name})"
    echo "  ======================================="
    process_file "${full_path}" "${build_subtype}"
    echo
  elif [[ ${build_name} =~ ${mandatory} ]]; then
    case "${build_type} ${build_subtype}" in "IP in" | "IP mono" | "OP in" | "OP assert")
                                               if [[ "${file}" == *mrun* ]]; then
                                                 cecho sWb "\"${build_type} ${build_subtype} mrun\" build not ready yet"
                                               else
                                                 cecho sWb "\"${build_type} ${build_subtype}\" build not ready yet"
                                               fi
                                               ;;
    esac
  fi
}  # show_tlog_if_present

function process_build {
  typeset -r build_name=$1
  cecho usBy "PROCESSING ${build_name} ..."
  build_subtypes="in mono assert lo hi memcheck with_secondary"

  for build_subtype in ${build_subtypes};do
    typeset tacot_corico_dir="${BASEDIR}/${build_name}/saved_logs/tacot_corico.LATEST"

    show_tlog_if_present "${build_name}" "${build_subtype}" "${tacot_corico_dir}" "Tlog-${build_subtype}.log"

    if [[ "${build_subtype}" == lo ]]; then
      lo_build_checks "${tacot_corico_dir}"
    fi

    tacot_corico_dir="${BASEDIR}/${build_name}/saved_logs/tacot_corico_mrun.LATEST_GOOD"
    show_tlog_if_present "${build_name}" "${build_subtype}" "${tacot_corico_dir}" "Tlog-mrun-${build_subtype}.log"
  done
}

function process_replay_logs {
  typeset -A mydict
  hr
  cecho sWr "REPLAYS"
  # using find is too slow !
  replay_files=$(ls -d "${BASEDIR%/}/build_${CM_ENV_ID/IP/OP}/saved_logs/Treplay_${CM_ENV_ID/IP/OP}_${FULL_BASELINE}"*.log 2>/dev/null)
  for file in ${replay_files};do
    replay_type=$(echo ${file} | awk -F'.' '{ print $(NF-2) }' | python3 -c "print(open(0).read().split('-')[-1])")
    mydict[${replay_type}]=${file}
  done
  unset AT_LEAST_ONE_REPLAY_FOUND
  for replay_type in run_prequal performance simca full_simca oldest_date all_autolink;do
    file=${mydict[${replay_type}]}
    if [[ -n ${file} ]]; then
      AT_LEAST_ONE_REPLAY_FOUND=True
      cechon sWb "$(printf "%-14s replay " "\"${replay_type}\"")"
      if grep -q "Executed UNINSTALL:\s*YES" "${file}";
      then
        cecho sWb "==> WAS SUCCESSFUL"
      elif grep -q "Executed UNINSTALL:\s*NO" "${file}";
      then
        cecho sWr "==> FAILED"
        echo_emacs "${file#./}"
        echo
        if "${VERBOSE}"; then
          # grep for SEVERE and remove the long path before the basename
          grep ERROR_REPORT.SEVERE "${file#./}" | sed 's/.*\/\([^/]*ERROR_REPORT\.SEVERE\)/\1/'
        fi
      elif ! grep -q 'Waiting for this replay to be finished' "${file}";
      then
        cecho sWb "---> WARNING: it looks like the replay hasn't started"
      else
        cecho sWb "IS STILL BUSY"
      fi
      hr '-'
    fi
  done
  if [[ -z ${AT_LEAST_ONE_REPLAY_FOUND} ]];then
    cecho sWb "WARNING: NO REPLAYS FOUND"
  fi
}  # process_replay_logs

function process_gnatcheck {
  hr
  cecho sWr "Padactl"
  if ! [[ ${available_builds} == *IP* ]]; then
    cecho sWb "WARNING: No IP (CRC runs in IP) for this build!"
    return
  fi
  CRC_BUILD=$(echo "${available_builds}" | grep -o "\bbuild.*IP.*\b")
  PADACTL_FILE="${BASEDIR}/${CRC_BUILD}/saved_logs/Padactl.LATEST/Padactl.summary"
  if [[ -f ${PADACTL_FILE} ]]; then
    hr '-'
    cecho sWb "${PADACTL_FILE}"
    grep -A20 delta "${PADACTL_FILE}"
    grep -A20 -i 'summary of last changes' "${PADACTL_FILE}"
    echo_emacs ${PADACTL_FILE}
  else
    cecho sWb "WARNING: No CRC summary file found!"
  fi
}

function check_replay_dirs_size {
  hr '-'
  cecho sWr "COMPUTE SIZE OF REPLAY DIRS"
  # check replay disk space for the past 7 days (with respect to current release)
  typeset total_size=0.0
  for replay_dir in $(ls -d ${CM_ROOT}/TACT/TACT_CONFIG![0-9]*/build_G!*OP*/saved_logs/replay_dir*)
  do
    cecho Wb "----------------------------------------------------------------------------------------------------"
    replay_type=$(python3 -c "print('${replay_dir}'.split('/')[-1].split('.')[0].split('-')[-1])")
    line=$(du --max-depth=0 -ch "${replay_dir}" 2>/dev/null | head -n1)
    SIZE="${line%%[[:space:]]*}"  # remove everything after the first space or tab
    cecho sBy "${replay_dir} ==> ${SIZE}"
    unit="${SIZE: -1}"
    if [[ "${unit}" != "G" ]]; then
      continue
    fi
    num_size="${SIZE%?}"  # remove the last character (the 'G' unit)
    build_saved_logs=$(dirname ${replay_dir})
    the_baseline=$(echo ${build_saved_logs} | cut -d! -f2 | cut -d/ -f1)
    replay_logfile=$(ls ${build_saved_logs}/Treplay*${replay_type}*log 2>/dev/null)
    if [[ ! -e ${replay_logfile} ]]; then
      # performance replay dir doesn't follow same naming convention as other replays
      replay_logfile=$(find "${replay_dir}" -type f -name "*replay_day.log" 2>/dev/null)
    fi
    if grep -q 'Replay terminated' "${replay_logfile}";
    then
      (( total_size += num_size ))  # only count the failed replays size
      printf "\tTO DELETE THIS FAILED REPLAY, 'su cmadm' (password=cm4all) and then\n"
      TACTDEV_REMOVE_CMD="${replay_dir}/tact/${the_baseline}/tactdev_remove"
      if [[ -f ${TACTDEV_REMOVE_CMD} ]];then
        printf '\t\t%s\n' "${TACTDEV_REMOVE_CMD}"
      else
        printf '\tNo tactdev_remove was found, use:\n'
        printf '\t\trm -fr ${replay_dir}\n'  # ?? replay_dir is not expanded!
      fi
    else
      printf "\t"
      cecho sfBy "THIS REPLAY IS STILL RUNNING"
      print '\tTo delete it, use the vncviewer from dhdevd01:99 and run:'
      print '\t\tTcleanup_old_replay_users -kill_replay'
    fi
  done
  echo
  cecho Wb "TOTAL SIZE for FAILED REPLAYS is $(printf "%.2f\n" "${total_size}")G"
  hr
}  # check_replay_dirs_size

function process_run_test_programs_log {
  echo
  hr
  cecho sWr "Check build closure and test programs."
  logfile=run_test_programs.log
  for build in ${available_builds}; do
    cecho usBy "CHECK RUN TEST PROGRAMS LOG FOR ${BASEDIR}/${build} ..."
    logfile=$(find "${BASEDIR}/${build}/saved_logs/tacot_corico.LATEST/work" -type f -name 'check_run_test_programs.log' -print -quit)

    if [[ -z "${logfile}" ]]; then
      if [[ "${FAST_MODE}" == 'true' ]]; then
        cecho sWb 'check_run_test_programs_log not yet complete and we are in fast mode -> skip this check.'
      else
        cecho sWb 'check_run_test_programs_log not yet complete -> execute the program manually. This can take some minutes (run with -f to disable the execution).'
        typeset build_subtype=${build#build_}
        (
          cd /tmp || exit 1
          # check_run_test_programs_log needs write permissions in the current working directory.
          echo check_run_test_programs_log | Ccontext -b "TACT.TACT_CONFIG.${FULL_BASELINE}" -e "${build_subtype}" 2>&1
        )
        # Do not filter in this case.
      fi
    else
      typeset full_report=$(cfmu_mktemp)
      echo "Full report is found in ${full_report}."
      echo
      cp "${logfile}" "${full_report}"
      grep -v 'Running.*setup' "${full_report}" |
        grep -v 'Checking for errors' |
        grep -v 'No errors found in' |
        grep -v -E '^[0-9.]+:\s+\S+\s+INFORMATION:' |
        grep -E '\S'
    fi

    break
  done
}  # process_run_test_programs_log

function create_dummy_view {
  if grep -q SIP <<< "${available_builds}"; then # Implies this is a weekend build.
    if zenity --question --text "Do you want to make a dummy view to protect the W-E build for valgrind?" --width=280; then
      echo "Csetup -e ${CM_ENV_ID} -b TACT.TACT_CONFIG.${FULL_BASELINE} DUMMY_t" | write2prompt
    fi
  fi
}
##################################################### MAIN ################################################
if "${COMPUTE_SIZE}"; then
  check_replay_dirs_size
else
  typeset -r FULL_BASELINE=${baseline_to_check} # e.g. 28.2.0.333
  typeset -r BASEDIR="/cm/ot/TACT/TACT_CONFIG.${FULL_BASELINE}"

  [[ ! -d "${BASEDIR}" ]] && cecho sWb "DIR ${BASEDIR} does not exist" && exit 1
  cd "${BASEDIR}" || exit 1
  cecho sWr "AVAILABLE BUILDS for ${BASEDIR}:"
  available_builds=$(show_available_builds | awk '{ print $(NF) }')
  echo "${available_builds}"
  process_builds "${available_builds}"
  process_replay_logs
  process_gnatcheck
  process_run_test_programs_log
  list_all_changes
  create_dummy_view
fi
