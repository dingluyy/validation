#!/bin/bash +x

nodes=(node-0 node-1 node-2 node-3 node-4)

tmux kill-session

ip link del dev br0 type bridge
ps -ef | grep "dnsmasq" |grep range | grep -v grep | awk '{print $2}' | sudo xargs kill

for node in "${nodes[@]}"; do
	echo "teardown for $node:"
	ip tuntap del dev ${node} mode tap || true
done;

STATE_DIR=$(dirname $0)/state
IMAGES_DIR=$(dirname $0)/images
rm -rf ${STATE_DIR}

docker ps -a | grep cnrancher/rancher:${TAG} | sudo xargs docker stop
docker ps -a | grep cnrancher/rancher:${TAG} | sudo xargs docker rm

tmux kill-session
