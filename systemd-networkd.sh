#!/bin/bash

export DEBIAN_FRONTEND=noninteractive
apt-get purge --yes resolvconf

systemctl disable NetworkManager
systemctl disable networking
systemctl disable wpa_supplicant.service
systemctl enable systemd-networkd.service
systemctl enable systemd-resolved.service
systemctl start systemd-resolved.service

rm /etc/resolv.conf
ln -s /run/systemd/resolve/resolv.conf /etc/resolv.conf

cat << EOF > /etc/systemd/network/99-default.network
[Network]
DHCP=yes
EOF

mkdir -p /etc/wpa_supplicant.d
cat << "EOF" > /etc/wpa_supplicant.d/genconfig.sh
#!/bin/bash
ifname=${1}
essid=${2}
passphrase=${3}

usage() {
  echo ""
  echo "Usage:"
  echo "  genconfig.sh <ifname> <ESSID> '<passphrase>'"
  echo ""
}

if [ $# -ne 3 ]; then
  usage
  exit 1
fi

wpa_passphrase ${essid} "${passphrase}" > /etc/wpa_supplicant.d/${ifname}.conf
chmod go-rwx /etc/wpa_supplicant.d/${ifname}.conf
EOF
chmod +x /etc/wpa_supplicant.d/genconfig.sh

cat > /etc/systemd/system/wpa_supplicant@.service << EOF
[Unit]
Description=WPA supplicant daemon (interface-specific version)
Requires=sys-subsystem-net-devices-%i.device
After=sys-subsystem-net-devices-%i.device
Before=network.target
Wants=network.target

[Service]
Type=simple
ExecStart=/sbin/wpa_supplicant -c/etc/wpa_supplicant.d/%I.conf -i%I

[Install]
Alias=multi-user.target.wants/wpa_supplicant@%i.service
EOF

