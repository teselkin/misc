#!/bin/bash
 
MYSQL_HOST=${MYSQL_HOST:-'127.0.0.1'}
MYSQL_USER=${MYSQL_USER:-''}
MYSQL_PASSWORD=${MYSQL_PASSWORD:-''}

MYSQL_CMD="mysql -h ${MYSQL_HOST}"
if [[ -n "${MYSQL_USER}" ]] && [[ -n "${MYSQL_PASSWORD}" ]]; then
    MYSQL_CMD="${MYSQL_CMD} -u ${MYSQL_USER} -p${MYSQL_PASSWORD}"
fi

function get_uuid {
    RETVAL=''
    local string=$1

    if [[ -z "${string}" ]]; then
        printf "No VM name given.\n"
        return
    fi

    printf "Searching for instance with display name '${string}' ... "
    local query="SELECT uuid FROM nova.instances WHERE instances.display_name = '${string}';"
    local uuid=$(${MYSQL_CMD} --batch --skip-column-names -e "${query}" | cut -d ' ' -f 2)

    if [[ -n "${uuid}" ]]; then
        printf 'found!\n'
        RETVAL="${uuid}"
        return
    fi
    printf 'not found.\n'

    printf "Searching for instance with UUID '${string}' ... "
    local query="SELECT uuid FROM nova.instances WHERE instances.uuid = '${string}';"
    local uuid=$(${MYSQL_CMD} --batch --skip-column-names -e "${query}" | cut -d ' ' -f 2)

    if [[ -n "${uuid}" ]]; then
        printf 'found!\n'
        RETVAL="${uuid}"
        return
    fi
    printf 'not found.\n'

    printf "Searching for instance with ID '${string}' ... "
    local query="SELECT uuid FROM nova.instances WHERE instances.id = '${string}';"
    local uuid=$(${MYSQL_CMD} --batch --skip-column-names -e "${query}" | cut -d ' ' -f 2)

    if [[ -n "${uuid}" ]]; then
        printf 'found!\n'
        RETVAL="${uuid}"
        return
    fi
    printf 'not found.\n'
}


function delete_instance {
    RETVAL=''
    local uuid=$1

    printf '\n'
    if [[ -z "${uuid}" ]]; then
        printf "No UUID given to delete instance records.\n"
        return
    fi

    printf "Deleting instance '${uuid}' ... "
    local query=$(cat <<EOF
DELETE FROM nova.instance_faults WHERE instance_faults.instance_uuid = '${uuid}';
DELETE FROM nova.instance_id_mappings WHERE instance_id_mappings.uuid = '${uuid}';
DELETE FROM nova.instance_info_caches WHERE instance_info_caches.instance_uuid = '${uuid}';
DELETE FROM nova.instance_system_metadata WHERE instance_system_metadata.instance_uuid = '${uuid}';
DELETE FROM nova.security_group_instance_association WHERE security_group_instance_association.instance_uuid = '${uuid}';
DELETE FROM nova.block_device_mapping WHERE block_device_mapping.instance_uuid = '${uuid}';
DELETE FROM nova.fixed_ips WHERE fixed_ips.instance_uuid = '${uuid}';
DELETE FROM nova.instance_actions_events WHERE instance_actions_events.action_id in (SELECT id from nova.instance_actions where instance_actions.instance_uuid = '${uuid}');
DELETE FROM nova.instance_actions WHERE instance_actions.instance_uuid = '${uuid}';
DELETE FROM nova.virtual_interfaces WHERE virtual_interfaces.instance_uuid = '${uuid}';
DELETE FROM nova.instances WHERE instances.uuid = '${uuid}';
EOF
)
    local result=$(${MYSQL_CMD} --batch --skip-column-names -e "${query}")

    printf 'done\n\n'
}

get_uuid $1
delete_instance ${RETVAL}


