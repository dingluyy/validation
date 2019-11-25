#!/bin/bash +x
set -e

sudo apt-get update
sudo apt-get install -y -q cloud-image-utils qemu-kvm
RANCHER_SERVER_VERSION=$1
RANCHER_CONTAINER_CIDR=$2
RANCHER_DHCP_RANGE=$3

TAG="${RANCHER_SERVER_VERSION:-v2.2.9-ent3-rc2}"
nodes=(node-0 node-1 node-2 node-3 node-4)

echo "setup br0:"

ip link add dev br0 type bridge
#ip addr add ${RANCHER_CONTAINER_CIDR:-172.20.0.1/16} brd + dev br0
ip addr add 172.20.0.1/16 brd + dev br0
ip link set br0 up
#dnsmasq --interface=br0 --bind-interfaces --dhcp-range=${RANCHER_DHCP_RANGE:-172.20.0.2,172.20.255.254}
dnsmasq --interface=br0 --bind-interfaces --dhcp-range=172.20.0.2,172.20.255.254
modprobe br_netfilter
sysctl net.bridge.bridge-nf-call-iptables=0

for node in "${nodes[@]}"; do
	echo "setup tun for $node:"
	ip tuntap add dev ${node} mode tap || true
	ip link set ${node} up promisc on || true
	ip link set ${node} master br0 || true
done;

#CLOUD_IMG=${DEFAULT_CLOUD_IMG:-https://cloud-images.ubuntu.com/bionic/current/bionic-server-cloudimg-amd64.img}
CLOUD_IMG="https://cloud-images.ubuntu.com/bionic/current/bionic-server-cloudimg-amd64.img"
STATE_DIR=$(dirname $0)/state
IMAGES_DIR=$(dirname $0)/images
LOCAL_IMG=${IMAGES_DIR}/$(basename ${CLOUD_IMG})

if [ ! -e ${LOCAL_IMG} ]; then
	mkdir -p ${IMAGES_DIR}
	curl -fL -o ${IMAGES_DIR}/$(basename ${CLOUD_IMG}) ${CLOUD_IMG}
fi

for node in "${nodes[@]}"; do
	echo "setup image for $node:"
	VM_IMG=${STATE_DIR}/${node}/hd.img
	USERDATA_IMG=${STATE_DIR}/${node}/user-data.img
	mkdir -p ${STATE_DIR}/${node}

	if [ ! -e ${VM_IMG} ]; then
		cp -v ${LOCAL_IMG} ${VM_IMG}
		qemu-img resize ${VM_IMG} +20G
	fi

	USERDATA_FILE=$(dirname $0)/user-data

	cat > ${USERDATA_FILE} <<EOF
#cloud-config
password: ubuntu
chpasswd: { expire: False }
ssh_pwauth: True
hostname: ${node}
bootcmd:
 - dhclient ens4
 - ip route del default via 172.20.0.1 dev ens4
runcmd:
 - curl https://releases.rancher.com/install-docker/18.06.sh | sh
 - usermod -aG docker ubuntu
 - echo 172.20.115.70 node-0 >> /etc/hosts
 - echo 172.20.115.71 node-1 >> /etc/hosts
 - echo 172.20.115.72 node-2 >> /etc/hosts
 - echo 172.20.115.73 node-3 >> /etc/hosts
 - echo 172.20.115.74 node-4 >> /etc/hosts
 - docker pull cnrancher/rancher:${TAG}
 - docker pull cnrancher/rancher-agent:${TAG}

EOF

	cloud-localds ${USERDATA_IMG} ${USERDATA_FILE}
	
	rm -f ${USERDATA_FILE}
	
done;
apt  install -y -q docker.io
docker run -d --restart=unless-stopped -p 8088:80 -p 8443:443 cnrancher/rancher:${TAG}
