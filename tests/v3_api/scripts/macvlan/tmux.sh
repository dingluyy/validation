#!/bin/bash +x

node_count=`env | grep 'RANCHER_NODE_COUNT' |awk -F'=' '{print $2}'`
node_count="${node_count:-3}"
if [ ${node_count} -gt 5 ];then
    node_count=5
fi
echo ${node_count}

tmux new-session -d -s kvm
for((i=0;i<${node_count};i++)){
    let j=i+1
    tmux new-window -t kvm:${j} -n node-${i}
    echo "tmux new-window -t kvm:${j} -n node-${i}"
    tmux send-keys -t kvm:${j} "sudo ./macvlan/run-kvm.sh --hostname node-${i}" C-m
    echo "tmux send-keys -t kvm:${j} \"sudo ./macvlan/run-kvm.sh --hostname node-${i}\" C-m"
}
tmux list-sessions