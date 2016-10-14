#!/bin/bash

csv_converter=$(mktemp)
cat << 'EOF' > ${csv_converter}
BEGIN {
  FS = ":"
  split("", repoinfo)
  split("", pkginfo)
  if (fields == "") {
    fields = "Repo-ID;Repo-Suite;Repo-Component;Repo-Architecture;\
Origin;Section;Package;Priority;Installed-Size;Architecture;\
Description;Original-Maintainer;Maintainer;Version;Filename;SHA256;\
Bugs;Description-md5;MD5sum;Depends;SHA1;Homepage;Size"
  }
  split(fields, csv_fields, ";")
  pkginfo_count = 0
  print_csv_header = 0
}

/^[[:space:]]*$/ {
  if (pkginfo_count > 0) {
    split("", arr)
    for (key in repoinfo) {
      arr[key] = repoinfo[key]
    }
    for (key in pkginfo) {
      arr[key] = pkginfo[key]
    }

    if (print_csv_header == 0) {
      print_csv_header = 1
      ostr = ""
      for(key in csv_fields) {
        ostr = ostr ";" csv_fields[key]
      }
      sub(/^;/, "", ostr)
      print ostr
    }

    ostr = ""
    for(key in csv_fields) {
      ostr = ostr ";" arr[csv_fields[key]]
    }
    sub(/^;/, "", ostr)
    print ostr

    pkginfo_count = 0
    split("", pkginfo)
  }
  next
}

/^Repo\-(ID|Suite|Component|Architecture)\:/ {
  repoinfo[$1] = substr($0, length($1) + 2)
  sub(/^[[:space:]]*/, "", repoinfo[$1])
  next
}

// {
  pkginfo[$1] = substr($0, length($1)+2)
  sub(/^[[:space:]]*/, "", pkginfo[$1])
  pkginfo_count += 1
  next
}
EOF

########################################

usage() {
  echo 'qwe'
}


parse_sources_list() {
  local action=$1
  local listfile=$2

  local arr
  local x
  local baseurl
  local suite
  local component
  local url
  local src_file
  local dst_suffix
  local dst_file
  local i

  while read line; do
    arr=(${line})
    x=0
    while [[ ! "${arr[$x]}" =~ ^(ftp|http|https): ]]; do
      ((x++))
    done
    baseurl=${arr[$x]}
    suite=${arr[(($x+1))]}
    for i in $(seq $(($x+2)) $((${#arr[@]}-1))); do
      component=${arr[$i]}
      if [[ -z "${component}" ]]; then
        continue
      fi
      url="${baseurl}/dists/${suite}/${component}/binary-${ARCH}"
      src_file="${url}/Packages"
      dst_suffix="${baseurl##*://}/${suite}/${component}/${ARCH}"
      dst_file="${CACHE_DIR}/${dst_suffix}/Packages"
      mkdir -p "${CACHE_DIR}/${dst_suffix}"
      case ${action} in
        list)
          if [[ -f "${dst_file}" ]]; then
            PACKAGES="${PACKAGES} ${dst_file}"
          fi
        ;;
        update)
          if [[ ! -f "${dst_file}" ]]; then
            echo "Downloading '${src_file}.gz' --> '${dst_file}.gz'"
            curl -L -s "${src_file}.gz" -o "${dst_file}.gz"
            gzip -d "${dst_file}.gz"
          fi
          if [[ -f "${dst_file}" ]]; then
            PACKAGES="${PACKAGES} ${dst_file}"
            cat << EOF > "${dst_file}.metadata"
Repo-ID: ${baseurl##*://}
Repo-Suite: ${suite}
Repo-Component: ${component}
Repo-Architecture: ${ARCH}
EOF
          fi
        ;;
        *)
          echo "Action '${action}' not known to parse_sources_list()"
        ;;
      esac
    done
  done < <(awk '/^deb[[:space:]]/{print $0}' ${listfile})
}


wipe_cache() {
  if [[ -d "${CACHE_DIR}" ]]; then
    rm -rf "${CACHE_DIR}"
  fi
  mkdir -p "${CACHE_DIR}"
}


process_cache() {
  local action=${1:-update}

  if [[ -n "${SOURCES_LIST}" && -f "${SOURCES_LIST}" ]]; then
    parse_sources_list ${action} ${SOURCES_LIST}
  fi

  if [[ -n "${SOURCES_LIST_DIR}" && -d "${SOURCES_LIST_DIR}" ]]; then
    for item in $(find ${SOURCES_LIST_DIR} -name '*.list' -type f); do
      parse_sources_list ${action} ${item}
    done
  fi
}


query_cache() {
  local tmpfile=$(mktemp)
  local outfile=$(mktemp)
  local name
  local cmd

  for filename in ${PACKAGES}; do
    >${tmpfile}
    if [[ -z "${INPUT_FILE}" ]]; then
      cmd="grep-dctrl ${QUERY} ${filename}"
      echo "> ${cmd}"
      eval "${cmd}" >> ${tmpfile}
    else
      while read name; do
        cmd="grep-dctrl ${QUERY} ${name} ${filename}"
        echo "> ${cmd}"
        eval "${cmd}" >> ${tmpfile}
      done < ${INPUT_FILE}
    fi
    if [[ $? -eq 0 ]]; then
      if [[ -f ${filename}.metadata ]]; then
        cat ${filename}.metadata >> ${outfile}
        echo '' >> ${outfile}
      fi
      cat ${tmpfile} >> ${outfile}
    fi
  done
  rm -f ${tmpfile}

  echo "Writing output file '${OUTPUT_FILE}'"
  if [[ -z "${CSV_FIELDS}" ]]; then
    cat ${outfile} >> ${OUTPUT_FILE}
  else
    awk -f ${csv_converter} -v fields=${CSV_FIELDS} ${outfile} >> ${OUTPUT_FILE}
  fi
  rm -f ${outfile}
}

########################################

CACHE_DIR='/tmp/deb-repoquery'
CONFIG_FILE=''
SOURCES_LIST=''
SOURCES_LIST_DIR=''
PACKAGES=''
ACTION=''
ARCH='amd64'
QUERY=''
CSV_FIELDS=''
INPUT_FILE=''
OUTPUT_FILE=''
WIPE_CACHE=false


while [[ -n "$1" ]]; do
  case "$1" in
    -h|--help)
      usage
      exit
    ;;
    -c|--config)
      CONFIG_FILE=$2
      shift
    ;;
    -s|--sources-list)
      SOURCES_LIST=$2
      shift
    ;;
    -S|--sources-list-dir)
      SOURCES_LIST_DIR=$2
      shift
    ;;
    -a|--arch)
      ARCH=$2
      shift
    ;;
    --csv)
      CSV_FIELDS="$2"
      shift
    ;;
    -f|--file)
      INPUT_FILE="$2"
      shift
    ;;
    -o|--output-file)
      OUTPUT_FILE="$2"
      shift
    ;;
    --wipe-cache)
      WIPE_CACHE=true
    ;;
    --)
      shift
      QUERY="$@"
      break
    ;;
    *)
      ACTION=$1
    ;;
  esac
  shift
done


if [[ -f "${CONFIG_FILE}" ]]; then
  source ${CONFIG_FILE}
fi

CACHE_DIR=${CACHE_DIR:-$(mktemp -d)}
if [[ ! -d "${CACHE_DIR}" ]]; then
  mkdir -p "${CACHE_DIR}"
fi

OUTPUT_FILE=${OUTPUT_FILE:-${INPUT_FILE}.out}
>${OUTPUT_FILE}

case ${ACTION} in
  update)
    if ${WIPE_CACHE}; then
      wipe_cache
    fi
    process_cache update
  ;;
  query)
    process_cache list
    query_cache
  ;;
  list)
    process_cache list
    echo "Got packages:"
    for item in ${PACKAGES}; do
      echo "* ${item}"
      if [[ -f ${item}.metadata ]]; then
        cat ${item}.metadata
      fi
    done
  ;;
  wipe-cache)
    wipe_cache
  ;;
  *)
    echo "Action '${ACTION}' is not supported"
  ;;
esac
