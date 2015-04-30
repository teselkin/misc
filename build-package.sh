#!/bin/bash

COMPONENT_DIR="$1"
MANIFESTS_DIR="$2"

pushd ${COMPONENT_DIR}
git reset --hard
git clean -fdx
package_name=$(python setup.py --name)
package_version=$(python setup.py --version)
python setup.py sdist
popd

pushd ${COMPONENT_DIR}/dist
cp ${package_name}-${package_version}.tar.gz ${package_name}_${package_version}.orig.tar.gz
tar xzvf ${package_name}-${package_version}.tar.gz
popd

cp -r ${MANIFESTS_DIR}/debian ${COMPONENT_DIR}/dist/${package_name}-${package_version}

# Build source package
pushd ${COMPONENT_DIR}/dist/${package_name}-${package_version}
dpkg-source -b .
popd

# Install build dependencies
pushd ${COMPONENT_DIR}/dist
sudo mk-build-deps -i *.dsc -t 'apt-get --no-install-recommends --yes --force-yes'
popd

pushd ${COMPONENT_DIR}/dist/${package_name}-${package_version}
dpkg-buildpackage -b -us -uc
popd

