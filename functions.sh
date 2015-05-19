#!/bin/bash

LOG_FILE=''
DEBUG=debug
DEBUG_LEVELS='error warn info debug'

# Usage:
#  echo 'Info message' | log
#  echo 'Debug message' | log debug
#  echo 'Error message' | log error
#  cat <<EOF | log
# Multiline
# string
# EOF

function log {
    local debug='info'
    local quiet='false'
    local log_cmd=''

    while [[ -n "$1" ]]; do
        case "$1" in
            'quiet') quiet='true' ;;
            *) debug="$1" ;;
        esac
        shift
    done

    # Check if requested debug level is not higher than default
    if [[ "$DEBUG_LEVELS " =~ ${DEBUG}.+${debug}[[:space:]] ]]; then
        return
    fi

    if [[ -n "$LOG_FILE" ]]; then
        log_cmd="$log_cmd | tee -a '$LOG_FILE'"
    fi

    if [[ "$quiet" == 'true' ]]; then
        log_cmd="$log_cmd >/dev/null"
    fi

    while read line; do
        line="$(date --rfc-3339=seconds) [${debug^^}] $line"
        eval "echo '$line' $log_cmd"
    done
}

