#!/bin/bash

function die {
    cat << EOF

STOP:
**********
$@
**********
EOF
    exit 1
}

function lxc_cmd {
    local name=$1
    shift
    sudo lxc-attach -n ${name} $@
}

export LC_ALL=C

LXC_ROOT=/var/lib/lxc

REF_IMAGE_DISTRO=${REF_IMAGE_DISTRO:-ubuntu}
REF_IMAGE_RELEASE=${REF_IMAGE_RELEASE:-trusty}
REF_IMAGE_NAME=${REF_IMAGE_DISTRO}-${REF_IMAGE_RELEASE}

REF_IMAGE_ID_RSA=~/.ssh/${REF_IMAGE_NAME}.id_rsa
REF_IMAGE_ROOT=${LXC_ROOT}/${REF_IMAGE_NAME}/rootfs

if sudo lxc-info -n ${REF_IMAGE_NAME}; then
    sudo lxc-destroy -f -n ${REF_IMAGE_NAME}
fi

sudo lxc-create -t ${REF_IMAGE_DISTRO} -n ${REF_IMAGE_NAME} -- -r ${REF_IMAGE_RELEASE}

CHROOT_UID=$(sudo chroot ${LXC_ROOT}/${REF_IMAGE_NAME}/fsroot id -u ubuntu)
CHROOT_GID=$(sudo chroot ${LXC_ROOT}/${REF_IMAGE_NAME}/fsroot id -g ubuntu)

sudo mkdir ${REF_IMAGE_ROOT}/home/ubuntu/.ssh

sudo cp ~/.ssh/keys/gerrit.mirantis.com.id_rsa ${REF_IMAGE_ROOT}/home/ubuntu/.ssh/review.fuel-infra.org.id_rsa
sudo chmod 400 ${REF_IMAGE_ROOT}/home/ubuntu/.ssh/review.fuel-infra.org.id_rsa

cat << EOF | sudo tee ${REF_IMAGE_ROOT}/home/ubuntu/.ssh/config
Host review.fuel-infra.org
    IdentityFile /home/ubuntu/.ssh/review.fuel-infra.org.id_rsa
    User dteselkin
EOF

rm -f ${REF_IMAGE_ID_RSA}
ssh-keygen -f ${REF_IMAGE_ID_RSA} -N ''
cat ${REF_IMAGE_ID_RSA}.pub | sudo tee ${REF_IMAGE_ROOT}/home/ubuntu/.ssh/authorized_keys
ssh-add ${REF_IMAGE_ID_RSA}

sudo chown -R ${CHROOT_UID}:${CHROOT_GID} ${REF_IMAGE_ROOT}/home/ubuntu/.ssh

echo 'ubuntu ALL=(ALL) NOPASSWD:ALL' | sudo tee ${REF_IMAGE_ROOT}/etc/sudoers.d/ubuntu
sudo chmod 440 ${REF_IMAGE_ROOT}/etc/sudoers.d/ubuntu

sudo lxc-start -n ${REF_IMAGE_NAME} -d

ip_addr=''
timeout=20
while [[ -z ${ip_addr} ]]; do
    sleep 1
    timeout=$((timeout-1))
    if [[ $timeout -le 0 ]]; then
        die "Timeout exceeded"
    fi
    ip_addr=$(sudo lxc-info -i -n ${REF_IMAGE_NAME} | awk '/IP\:/{print $2}')
done
echo "Timeout: ${timeout} second(s) left"

lxc_cmd ${REF_IMAGE_NAME} apt-get update
lxc_cmd ${REF_IMAGE_NAME} apt-get upgrade --yes
lxc_cmd ${REF_IMAGE_NAME} apt-get install --yes git devscripts equivs python-setuptools python-pip python-dev
lxc_cmd ${REF_IMAGE_NAME} poweroff

