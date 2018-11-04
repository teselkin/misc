#!/bin/bash

set -o errexit
#set -o xtrace

# -----BEGIN_BUNDLE_BODY-----

declare -a ARGS
declare -A KWARGS
KWARGS['ofile']=$0.out
KWARGS['odir']=~/.local/mos-validation-tool
KWARGS['force']='false'

function die {
    cat << EOF
=====
$@
=====
EOF
    exit 1
}

function pack {
    local ofile=$(readlink -m ${KWARGS['ofile']})
    local template=${0}

    mkdir -p ${ofile%/*} ||:

    # Add header
    cat << EOF > "${ofile}"
#!/bin/bash

set -o errexit
#set -o xtrace
EOF

    # Add body
    echo '' >> ${ofile}
    awk '
$2 == "-----END_BUNDLE_BODY-----" {print $0; exit}
f == 1 {print $0; next}
$2 == "-----BEGIN_BUNDLE_BODY-----" {f=1; print $0; next}
' "${template}" >> "${ofile}"

    # Add archive
    echo '' >> ${ofile}
    echo '# -----BEGIN_BUNDLE_ARCHIVE-----' >> ${ofile}
    tar czv ${ARGS[1]} | base64 | awk '{print "# " $0}' >> ${ofile}
    echo '# -----END_BUNDLE_ARCHIVE-----' >> ${ofile}
}

function unpack {
    local odir=${KWARGS['odir']}
	local bundle=${0}

    awk '
$2 == "-----END_BUNDLE_ARCHIVE-----" {exit}
f == 1 {print $2; next}
$2 == "-----BEGIN_BUNDLE_ARCHIVE-----" {f=1;next}
' ${bundle} | base64 -d | tar xzv -C "${odir}"
}

function usage {
    cat << EOF

Usage:

    bundle.sh <command>

Commands:

    pack [--ofile <output file name>] dir [dir[...dir]]
    unpack dir
    run

EOF
    exit
}

function run {
    unpack
    PYTHONPATH="${KWARGS['odir']}:$PYTHONPATH" python ${KWARGS['odir']}/certification_tool/main.py $@
}

while [[ -n "${1}" ]]; do
    case "${1}" in
        --force)
            KWARGS['force']='true'
            shift
        ;;
        --*)
            KWARGS[${1#--}]=$2
            shift 2
        ;;
        *)
            ARGS[${#ARGS[@]}]=$1
            shift
        ;;
    esac
done


if [[ ',pack,unpack,run,' =~ ,${ARGS[0]}, ]]; then
    ${ARGS[0]}
else
    echo "Unknown command ${ARGS[0]}"
    usage
fi

exit

# -----END_BUNDLE_BODY-----
