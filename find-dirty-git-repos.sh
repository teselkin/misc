#!/bin/bash
#set -o xtrace

rootdir=${1:-~/workspace/git}

pushd() {
  command pushd "${@}" > /dev/null
}

popd() {
  command popd "${@}" > /dev/null
}

statefile=$(mktemp)
for path in $(find ${rootdir} -name '.git' -type d); do
  path=${path%/.git}
  #echo ${path}
  pushd ${path}
  #git fetch
  dirty=false
  >${statefile}
  if [[ $(git status --porcelain | wc -l) -gt 0 ]]; then
    dirty=true
    echo "* DIRTY" >> ${statefile}
  fi
  git branch -vv \
    | perl -pe 's/(\*|\s)\s((?:\w|[\/\.])+)\s+(\w+)\s+\[((?:\w|[\.\/])+)(?:\:\s(.+?))?\]\s+(.+)/\3|\4|\5/p' \
    | while IFS='|' read _local _remote _diff; do
      if [[ -n "${_diff}" ]]; then
        dirty=true
        echo "* $_local .. $_remote --> $_diff" >> ${statefile}
      fi
  done
  if $dirty; then
    echo ${path}
    cat ${statefile}
  fi
  popd
done

